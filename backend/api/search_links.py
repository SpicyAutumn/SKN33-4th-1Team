"""Private permalinks and explicit, unlisted public sharing of answer snapshots."""
import hashlib
import secrets
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .models import SearchRecord, SearchResult

GUEST_COOKIE = "heritage_search_guest"
GUEST_MAX_AGE = 30 * 24 * 60 * 60
ANSWER_FIELDS = {
    "schema_version", "request_id", "interaction_id", "response_type", "message",
    "summary", "clarification", "premise_correction", "warnings", "citations", "media",
}


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def save_result(request, answer, question, level, session, record):
    token = request.COOKIES.get(GUEST_COOKIE) or secrets.token_urlsafe(32)
    snapshot = {key: value for key, value in answer.items() if key in ANSWER_FIELDS}
    snapshot.update(question=question, audience_level=level,
                    search_record_id=str(record.id) if record else None)
    result = SearchResult.objects.create(
        id=record.id if record else uuid.uuid4(),
        owner=session.user if session else None,
        guest_token_hash="" if session else _digest(token), payload=snapshot,
    )
    response = JsonResponse({**answer, **_private_data(result)})
    response["Cache-Control"] = "private, no-store"
    if not session:
        response.set_cookie(GUEST_COOKIE, token, max_age=GUEST_MAX_AGE,
                            httponly=True, secure=settings.SESSION_COOKIE_SECURE,
                            samesite="Lax", path="/")
    return response


def _private_data(result):
    return {**result.payload, "search_result_id": str(result.id),
            "created_at": result.created_at.isoformat(),
            "share_path": f"/share/{result.share_token}" if result.share_token else None}


def _owned_result(request, result_id):
    from .views import _current_session, _record_data
    session = _current_session(request)
    result = SearchResult.objects.filter(id=result_id).first()
    if result:
        if result.owner_id:
            return result if session and session.user_id == result.owner_id else None
        token = request.COOKIES.get(GUEST_COOKIE, "")
        return result if token and secrets.compare_digest(result.guest_token_hash, _digest(token)) else None
    # Records made before this feature still have working private links.
    if session:
        record = SearchRecord.objects.filter(id=result_id, owner=session.user).prefetch_related("citations").first()
        if record:
            payload = _record_data(record, detail=True, include_media=True)
            payload["search_record_id"] = str(record.id)
            return SearchResult(id=record.id, owner=session.user, payload=payload, created_at=record.created_at)
    return None


def _not_found():
    from .views import _error
    return _error("RESOURCE_NOT_FOUND", "결과를 찾을 수 없거나 접근 권한이 없습니다. 본인의 검색은 로그인하거나 검색했던 브라우저에서 열어 주세요.", 404)


@never_cache
@require_GET
def search_result(request, result_id):
    result = _owned_result(request, result_id)
    return JsonResponse(_private_data(result)) if result else _not_found()


@never_cache
@require_POST
def share_result(request, result_id):
    result = _owned_result(request, result_id)
    if result is None:
        return _not_found()
    if result._state.adding:
        result, _ = SearchResult.objects.get_or_create(id=result.id, defaults={
            "owner": result.owner, "payload": result.payload,
        })
    # Conditional update makes repeated/concurrent clicks return one stable link.
    SearchResult.objects.filter(id=result.id, share_token__isnull=True).update(share_token=uuid.uuid4())
    result.refresh_from_db(fields=["share_token"])
    return JsonResponse({"share_path": f"/share/{result.share_token}"})


@never_cache
@require_GET
def shared_result(request, share_token):
    result = SearchResult.objects.filter(share_token=share_token).first()
    if result is None:
        return _not_found()
    allowed = ANSWER_FIELDS - {"request_id", "interaction_id"}
    payload = {key: value for key, value in result.payload.items() if key in allowed}
    payload.update(question=result.payload["question"], audience_level=result.payload["audience_level"],
                   shared=True, share_path=f"/share/{result.share_token}")
    response = JsonResponse(payload)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response

