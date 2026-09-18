import hashlib
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import AuthSession, ErrorReport, ErrorReportQuote, ErrorReportType, SearchCitation, SearchRecord, ServiceUser
from .rag_runtime import RagUnavailableError, answer as rag_answer

SESSION_COOKIE = "heritage_session"
SESSION_DAYS = 7
LEVELS = {"easy", "general", "advanced"}
REPORT_CATEGORIES = {"incorrect_fact", "citation_mismatch", "incomplete_answer", "inappropriate_content", "image_problem", "feature_error", "other"}


def _payload(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _error(code, message, status=400, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JsonResponse(body, status=status)


def _user_data(user):
    return {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role, "created_at": user.created_at.isoformat()}


def _current_session(request):
    token = request.COOKIES.get(SESSION_COOKIE, "")
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = AuthSession.objects.select_related("user").filter(
        token_hash=token_hash, revoked_at__isnull=True, expires_at__gt=timezone.now(), user__is_active=True
    ).first()
    if session:
        AuthSession.objects.filter(pk=session.pk).update(last_seen_at=timezone.now())
    return session


def _require_session(request):
    session = _current_session(request)
    if session is None:
        return None, _error("AUTHENTICATION_REQUIRED", "로그인 후 이용할 수 있습니다.", 401)
    return session, None


def _set_session_cookie(response, user):
    token = secrets.token_urlsafe(48)
    now = timezone.now()
    AuthSession.objects.create(
        user=user,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=now + timedelta(days=SESSION_DAYS),
        last_seen_at=now,
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    return response


def _citation_data(citation):
    return {
        "chunk_id": citation.chunk_id,
        "document_id": citation.document_id,
        "title": citation.title,
        "source_url": citation.source_url,
        "section": citation.section,
        "retrieval_rank": citation.retrieval_rank,
        "content": citation.content,
    }


def _record_data(record, detail=False):
    data = {
        "id": str(record.id),
        "question": record.question,
        "audience_level": record.audience_level,
        "response_type": record.response_type,
        "answer_preview": record.message[:160],
        "citation_count": record.citations.count() if detail else getattr(record, "citation_count", 0),
        "created_at": record.created_at.isoformat(),
    }
    if detail:
        data.update({
            "schema_version": record.schema_version,
            "request_id": record.rag_request_id,
            "interaction_id": record.interaction_id or None,
            "message": record.message,
            "clarification": record.clarification,
            "premise_correction": record.premise_correction,
            "warnings": record.warnings,
            "citations": [_citation_data(item) for item in record.citations.all()],
        })
    return data


def _report_data(report, detail=False):
    """Serialize both legacy and multi-select error-report fields."""
    categories = [item.code for item in report.types.all()]
    # Reports made before the multi-select release have no child type rows.
    if not categories and report.category:
        categories = [report.category]
    data = {
        "id": str(report.id),
        "search_record_id": str(report.search_record_id),
        "category": report.category,
        "categories": categories,
        "status": report.status,
        "question_preview": report.search_record.question[:120],
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
    }
    if detail:
        data.update({
            "content": report.content,
            "staff_reply": report.staff_reply,
            "question": report.search_record.question,
            "answer_preview": report.search_record.message[:160],
            "selected_quotes": [
                {
                    "id": item.id,
                    "text": item.text,
                    "start_offset": item.start_offset,
                    "end_offset": item.end_offset,
                }
                for item in report.selected_quotes.all()
            ],
        })
    return data


def _report_categories(payload):
    """Accept the new `categories` array and the current UI's `category`."""
    raw_categories = payload.get("categories")
    if raw_categories is None:
        raw_categories = [payload.get("category")]
    if not isinstance(raw_categories, list):
        return None
    categories = []
    for item in raw_categories:
        code = str(item or "").strip()
        if code not in REPORT_CATEGORIES:
            return None
        if code not in categories:
            categories.append(code)
    return categories or None


def _selected_quotes(payload, answer_text):
    """Validate up to five independently selected answer passages.

    A quote can be sent without offsets until the sentence-selection UI is
    released. When offsets are sent, they must point to exactly the selected
    text in the stored answer; this distinguishes repeated sentences safely.
    """
    raw_quotes = payload.get("selected_quotes", [])
    if raw_quotes is None:
        raw_quotes = []
    if not isinstance(raw_quotes, list) or len(raw_quotes) > 5:
        return None
    quotes = []
    for item in raw_quotes:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            return None
        text = item["text"]
        if not text.strip() or len(text) > 2000:
            return None
        start_offset = item.get("start_offset")
        end_offset = item.get("end_offset")
        if (start_offset is None) != (end_offset is None):
            return None
        if start_offset is not None:
            if (
                isinstance(start_offset, bool)
                or isinstance(end_offset, bool)
                or not isinstance(start_offset, int)
                or not isinstance(end_offset, int)
                or start_offset < 0
                or end_offset <= start_offset
                or end_offset > len(answer_text)
                or answer_text[start_offset:end_offset] != text
            ):
                return None
        quotes.append({"text": text, "start_offset": start_offset, "end_offset": end_offset})
    return quotes


@require_GET
def health(_request):
    return JsonResponse({"status": "ok", "chat_mode": "rag", "api_version": "v1"})


@ensure_csrf_cookie
@require_GET
def csrf(_request):
    return JsonResponse({"csrf_token": get_token(_request)})


@require_POST
def signup(request):
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if not 1 <= len(name) <= 50 or not email or len(password) < 8:
        return _error("VALIDATION_ERROR", "이름, 이메일, 8자 이상 비밀번호를 입력해 주세요.", 422)
    if ServiceUser.objects.filter(email=email).exists():
        return _error("EMAIL_ALREADY_EXISTS", "이미 사용 중인 이메일입니다.", 409)
    user = ServiceUser.objects.create(email=email, name=name, password_hash=make_password(password))
    return _set_session_cookie(JsonResponse(_user_data(user), status=201), user)


@require_POST
def login_view(request):
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = ServiceUser.objects.filter(email=email, is_active=True).first()
    if user is None or not check_password(password, user.password_hash):
        return _error("INVALID_CREDENTIALS", "이메일 또는 비밀번호를 확인해 주세요.", 401)
    return _set_session_cookie(JsonResponse(_user_data(user)), user)


@require_POST
def logout_view(request):
    session = _current_session(request)
    if session:
        AuthSession.objects.filter(pk=session.pk).update(revoked_at=timezone.now())
    response = JsonResponse({}, status=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@ensure_csrf_cookie
@require_GET
def me(request):
    session = _current_session(request)
    if session is None:
        return _error("AUTHENTICATION_REQUIRED", "로그인이 필요합니다.", 401)
    return JsonResponse(_user_data(session.user))


@require_POST
def searches(request):
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    question = str(payload.get("question", "")).strip()
    audience_level = str(payload.get("audience_level", "general"))
    if not question or len(question) > 1000 or audience_level not in LEVELS:
        return _error("VALIDATION_ERROR", "질문 또는 설명 수준을 확인해 주세요.", 422)
    try:
        response = rag_answer(question, audience_level=audience_level)
    except RagUnavailableError:
        return _error("RAG_UPSTREAM_ERROR", "지금은 자료를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", 502)

    session = _current_session(request)
    record = None
    if session:
        with transaction.atomic():
            record = SearchRecord.objects.create(
                owner=session.user,
                rag_request_id=str(response.get("request_id") or secrets.token_hex(16))[:80],
                interaction_id=str(response.get("interaction_id") or "")[:80],
                schema_version=str(response.get("schema_version") or "0.3.0-draft")[:30],
                question=question,
                audience_level=audience_level,
                response_type=str(response.get("response_type") or "answered")[:40],
                message=str(response.get("message") or ""),
                clarification=response.get("clarification"),
                premise_correction=response.get("premise_correction"),
                warnings=response.get("warnings") or [],
            )
            for ordinal, item in enumerate(response.get("citations") or [], start=1):
                SearchCitation.objects.create(
                    search_record=record,
                    ordinal=ordinal,
                    chunk_id=str(item.get("chunk_id") or f"citation-{ordinal}"),
                    document_id=str(item.get("document_id") or ""),
                    title=str(item.get("title") or "출처"),
                    source_url=str(item.get("source_url") or ""),
                    section=str(item.get("section") or ""),
                    retrieval_rank=int(item.get("retrieval_rank") or ordinal),
                    content=str(item.get("content") or ""),
                )
    return JsonResponse({**response, "search_record_id": str(record.id) if record else None, "created_at": record.created_at.isoformat() if record else None})


@require_GET
def my_searches(request):
    session, error = _require_session(request)
    if error:
        return error
    try:
        limit = min(max(int(request.GET.get("limit", 20)), 1), 100)
    except ValueError:
        return _error("VALIDATION_ERROR", "limit 값을 확인해 주세요.", 422)
    records = list(SearchRecord.objects.filter(owner=session.user).prefetch_related("citations")[:limit])
    return JsonResponse({"items": [_record_data(item, detail=True) for item in records], "next_cursor": None})


@require_GET
def my_search_detail(request, record_id):
    session, error = _require_session(request)
    if error:
        return error
    record = SearchRecord.objects.filter(id=record_id, owner=session.user).prefetch_related("citations").first()
    if record is None:
        return _error("RESOURCE_NOT_FOUND", "검색 기록을 찾을 수 없습니다.", 404)
    return JsonResponse(_record_data(record, detail=True))


@require_http_methods(["GET", "POST"])
def error_reports(request):
    session, error = _require_session(request)
    if error:
        return error
    if request.method == "GET":
        reports = ErrorReport.objects.filter(owner=session.user).select_related("search_record").prefetch_related("types")[:20]
        return JsonResponse({"items": [_report_data(item) for item in reports], "next_cursor": None})
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    record = SearchRecord.objects.filter(id=payload.get("search_record_id"), owner=session.user).first()
    categories = _report_categories(payload)
    selected_quotes = _selected_quotes(payload, record.message) if record else None
    content = str(payload.get("content", "")).strip()
    if record is None:
        return _error("RESOURCE_NOT_FOUND", "검색 기록을 찾을 수 없습니다.", 404)
    if categories is None:
        return _error("VALIDATION_ERROR", "제보 유형을 한 개 이상 선택해 주세요.", 422)
    if selected_quotes is None:
        return _error("VALIDATION_ERROR", "선택 문장은 최대 5개까지, 답변의 실제 문장만 제보할 수 있습니다.", 422)
    content_required = not selected_quotes or "other" in categories
    if len(content) > 2000 or (content_required and len(content) < 10):
        message = "추가 설명은 2,000자 이내로 입력해 주세요. 선택 문장이 없거나 기타 유형이면 10자 이상 필요합니다."
        return _error("VALIDATION_ERROR", message, 422)
    with transaction.atomic():
        # category remains populated for current clients and legacy data tools.
        report = ErrorReport.objects.create(
            owner=session.user,
            search_record=record,
            category=categories[0],
            content=content,
        )
        ErrorReportType.objects.bulk_create([
            ErrorReportType(error_report=report, code=code) for code in categories
        ])
        ErrorReportQuote.objects.bulk_create([
            ErrorReportQuote(
                error_report=report,
                ordinal=ordinal,
                text=item["text"],
                start_offset=item["start_offset"],
                end_offset=item["end_offset"],
            )
            for ordinal, item in enumerate(selected_quotes, start=1)
        ])
    report = ErrorReport.objects.select_related("search_record").prefetch_related("types", "selected_quotes").get(id=report.id)
    return JsonResponse(_report_data(report, detail=True), status=201)


@require_GET
def my_error_report_detail(request, report_id):
    session, error = _require_session(request)
    if error:
        return error
    report = ErrorReport.objects.filter(id=report_id, owner=session.user).select_related("search_record").prefetch_related("types", "selected_quotes").first()
    if report is None:
        return _error("RESOURCE_NOT_FOUND", "오류 제보를 찾을 수 없습니다.", 404)
    return JsonResponse(_report_data(report, detail=True))
