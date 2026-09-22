import hashlib
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .media_catalog import media_catalog_status, media_for_citations
from .models import AuthSession, ErrorReport, SearchCitation, SearchRecord, ServiceUser
from .rag_runtime import RagUnavailableError, answer as rag_answer

SESSION_COOKIE = "heritage_session"
SESSION_DAYS = 7
ADMIN_SESSION_COOKIE = "heritage_admin_session"
ADMIN_SESSION_SECONDS = 8 * 60 * 60
LEVELS = {"easy", "general", "advanced"}
REPORT_CATEGORIES = {"incorrect_fact", "citation_mismatch", "incomplete_answer", "inappropriate_content", "other"}
REPORT_STATUSES = {"received", "reviewing", "completed"}


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


def _admin_session_is_valid(request):
    token = request.COOKIES.get(ADMIN_SESSION_COOKIE, "")
    if not token:
        return False
    try:
        return signing.TimestampSigner(salt="heritage-admin-dashboard").unsign(token, max_age=ADMIN_SESSION_SECONDS) == "dashboard"
    except (signing.BadSignature, signing.SignatureExpired):
        return False


def _require_admin(request):
    if not settings.ADMIN_DASHBOARD_PASSWORD:
        return None, _error("ADMIN_PASSWORD_NOT_CONFIGURED", "관리자 비밀번호가 설정되지 않았습니다.", 503)
    if not _admin_session_is_valid(request):
        return None, _error("ADMIN_PASSWORD_REQUIRED", "관리자 비밀번호를 입력해 주세요.", 401)
    return True, None


def _set_admin_session_cookie(response):
    token = signing.TimestampSigner(salt="heritage-admin-dashboard").sign("dashboard")
    response.set_cookie(
        ADMIN_SESSION_COOKIE,
        token,
        max_age=ADMIN_SESSION_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    return response


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


def _record_data(record, detail=False, include_media=False):
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
        citations = [_citation_data(item) for item in record.citations.all()]
        data.update({
            "schema_version": record.schema_version,
            "request_id": record.rag_request_id,
            "interaction_id": record.interaction_id or None,
            "message": record.message,
            "clarification": record.clarification,
            "premise_correction": record.premise_correction,
            "warnings": record.warnings,
            "citations": citations,
        })
        if include_media:
            data["media"] = media_for_citations(citations)
    return data


@require_GET
def health(_request):
    media_status = media_catalog_status()
    return JsonResponse({
        "status": "ok",
        "chat_mode": "rag",
        "api_version": "v1",
        "media_catalog": "available" if media_status["available"] else "missing",
    })


@ensure_csrf_cookie
@require_GET
def csrf(_request):
    return JsonResponse({"csrf_token": get_token(_request)})


@require_GET
def admin_session(request):
    if not settings.ADMIN_DASHBOARD_PASSWORD:
        return _error("ADMIN_PASSWORD_NOT_CONFIGURED", "관리자 비밀번호가 설정되지 않았습니다.", 503)
    return JsonResponse({"authenticated": _admin_session_is_valid(request)})


@require_POST
def admin_login(request):
    if not settings.ADMIN_DASHBOARD_PASSWORD:
        return _error("ADMIN_PASSWORD_NOT_CONFIGURED", "관리자 비밀번호가 설정되지 않았습니다.", 503)
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    password = str(payload.get("password", ""))
    if not secrets.compare_digest(password, settings.ADMIN_DASHBOARD_PASSWORD):
        return _error("INVALID_ADMIN_PASSWORD", "관리자 비밀번호를 확인해 주세요.", 401)
    return _set_admin_session_cookie(JsonResponse({"authenticated": True}))


@require_POST
def admin_logout(request):
    response = JsonResponse({}, status=204)
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
    return response


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


@require_http_methods(["GET", "PATCH", "DELETE"])
def my_profile(request):
    """Read, update, or permanently remove the signed-in member's account."""
    session, error = _require_session(request)
    if error:
        return error
    user = session.user
    if request.method == "GET":
        return JsonResponse(_user_data(user))

    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")

    if request.method == "PATCH":
        name = str(payload.get("name", user.name)).strip()
        email = str(payload.get("email", user.email)).strip().lower()
        email_changed = email != user.email
        if not 1 <= len(name) <= 50 or not email:
            return _error("VALIDATION_ERROR", "이름과 이메일을 확인해 주세요.", 422)
        if email_changed:
            current_password = str(payload.get("current_password", ""))
            if not check_password(current_password, user.password_hash):
                return _error("INVALID_CREDENTIALS", "이메일을 바꾸려면 현재 비밀번호를 입력해 주세요.", 401)
            if ServiceUser.objects.exclude(pk=user.pk).filter(email=email).exists():
                return _error("EMAIL_ALREADY_EXISTS", "이미 사용 중인 이메일입니다.", 409)
        user.name = name
        user.email = email
        user.save(update_fields=["name", "email", "updated_at"])
        return JsonResponse(_user_data(user))

    current_password = str(payload.get("current_password", ""))
    if not check_password(current_password, user.password_hash):
        return _error("INVALID_CREDENTIALS", "현재 비밀번호를 확인해 주세요.", 401)
    if str(payload.get("confirmation", "")).strip() != "탈퇴":
        return _error("VALIDATION_ERROR", "탈퇴 확인란에 '탈퇴'를 입력해 주세요.", 422)
    with transaction.atomic():
        # These relations are deliberately RESTRICT in the schema, so delete a
        # member's private records explicitly before removing the account.
        ErrorReport.objects.filter(owner=user).delete()
        SearchRecord.objects.filter(owner=user).delete()
        AuthSession.objects.filter(user=user).delete()
        user.delete()
    response = JsonResponse({}, status=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@require_POST
def my_password(request):
    session, error = _require_session(request)
    if error:
        return error
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    current_password = str(payload.get("current_password", ""))
    new_password = str(payload.get("new_password", ""))
    if not check_password(current_password, session.user.password_hash):
        return _error("INVALID_CREDENTIALS", "현재 비밀번호를 확인해 주세요.", 401)
    if len(new_password) < 8:
        return _error("VALIDATION_ERROR", "새 비밀번호는 8자 이상으로 입력해 주세요.", 422)
    session.user.password_hash = make_password(new_password)
    session.user.save(update_fields=["password_hash", "updated_at"])
    # Keep this browser logged in, but invalidate every other device.
    AuthSession.objects.filter(user=session.user).exclude(pk=session.pk).update(revoked_at=timezone.now())
    return JsonResponse({"message": "비밀번호를 변경했습니다."})


@require_POST
def searches(request):
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    question = str(payload.get("question", "")).strip()
    audience_level = str(payload.get("audience_level", "general"))
    interaction_id = payload.get("interaction_id")
    clarification_context = payload.get("clarification_context")
    selected_source_chunk_ids = payload.get("selected_source_chunk_ids", [])
    if not question or len(question) > 1000 or audience_level not in LEVELS:
        return _error("VALIDATION_ERROR", "질문 또는 설명 수준을 확인해 주세요.", 422)
    if interaction_id is not None and (not isinstance(interaction_id, str) or not interaction_id.strip()):
        return _error("VALIDATION_ERROR", "추가 질문 연결 정보를 확인해 주세요.", 422)
    if clarification_context is not None and not isinstance(clarification_context, dict):
        return _error("VALIDATION_ERROR", "추가 질문 내용을 확인해 주세요.", 422)
    if (
        not isinstance(selected_source_chunk_ids, list)
        or len(selected_source_chunk_ids) > 3
        or any(
            not isinstance(chunk_id, str)
            or not chunk_id.strip()
            or len(chunk_id) > 512
            for chunk_id in selected_source_chunk_ids
        )
    ):
        return _error("VALIDATION_ERROR", "선택한 근거 정보를 확인해 주세요.", 422)
    if selected_source_chunk_ids and (clarification_context is None or interaction_id is None):
        return _error("VALIDATION_ERROR", "선택한 근거에는 추가 질문 연결 정보가 필요합니다.", 422)
    try:
        response = rag_answer(
            question,
            audience_level=audience_level,
            interaction_id=interaction_id.strip() if isinstance(interaction_id, str) else None,
            clarification_context=clarification_context,
            selected_source_chunk_ids=[chunk_id.strip() for chunk_id in selected_source_chunk_ids],
        )
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
    return JsonResponse(_record_data(record, detail=True, include_media=True))


@require_http_methods(["GET", "POST"])
def error_reports(request):
    session, error = _require_session(request)
    if error:
        return error
    if request.method == "GET":
        reports = ErrorReport.objects.filter(owner=session.user).select_related("search_record")[:20]
        return JsonResponse({"items": [{"id": str(item.id), "search_record_id": str(item.search_record_id), "category": item.category, "status": item.status, "question_preview": item.search_record.question[:120], "content_preview": item.content[:160], "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()} for item in reports], "next_cursor": None})
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    record = SearchRecord.objects.filter(id=payload.get("search_record_id"), owner=session.user).first()
    category = str(payload.get("category", ""))
    content = str(payload.get("content", "")).strip()
    if record is None:
        return _error("RESOURCE_NOT_FOUND", "검색 기록을 찾을 수 없습니다.", 404)
    if category not in REPORT_CATEGORIES or not 10 <= len(content) <= 2000:
        return _error("VALIDATION_ERROR", "제보 유형과 10~2000자 내용을 확인해 주세요.", 422)
    report = ErrorReport.objects.create(owner=session.user, search_record=record, category=category, content=content)
    return JsonResponse({"id": str(report.id), "search_record_id": str(record.id), "category": report.category, "content": report.content, "status": report.status, "staff_reply": None, "created_at": report.created_at.isoformat(), "updated_at": report.updated_at.isoformat()}, status=201)


@require_GET
def my_error_report_detail(request, report_id):
    session, error = _require_session(request)
    if error:
        return error
    report = ErrorReport.objects.filter(id=report_id, owner=session.user).select_related("search_record").first()
    if report is None:
        return _error("RESOURCE_NOT_FOUND", "오류 제보를 찾을 수 없습니다.", 404)
    return JsonResponse({"id": str(report.id), "search_record_id": str(report.search_record_id), "category": report.category, "content": report.content, "status": report.status, "staff_reply": report.staff_reply, "question": report.search_record.question, "answer_preview": report.search_record.message[:160], "answer_text": report.search_record.message, "created_at": report.created_at.isoformat(), "updated_at": report.updated_at.isoformat()})


def _admin_report_data(report, detail=False):
    data = {
        "id": str(report.id),
        "category": report.category,
        "content_preview": report.content[:160],
        "status": report.status,
        "question_preview": report.search_record.question[:120],
        "reporter_name": report.owner.name,
        "reporter_email": report.owner.email,
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
    }
    if detail:
        data.update({
            "search_record_id": str(report.search_record_id),
            "question": report.search_record.question,
            "content": report.content,
            "answer_text": report.search_record.message,
            "staff_reply": report.staff_reply or "",
            "handled_by_name": report.handled_by.name if report.handled_by else None,
            "handled_at": report.handled_at.isoformat() if report.handled_at else None,
        })
    return data


def _dashboard_recent_users(limit=6, offset=0):
    """Return one most-recent active session per user for the operator dashboard."""
    sessions = AuthSession.objects.select_related("user").filter(
        revoked_at__isnull=True,
        last_seen_at__isnull=False,
    ).order_by("-last_seen_at", "-created_at")
    users = []
    seen_user_ids = set()
    for item in sessions.iterator():
        if item.user_id in seen_user_ids:
            continue
        seen_user_ids.add(item.user_id)
        if len(seen_user_ids) <= offset:
            continue
        users.append({
            "id": str(item.user_id),
            "name": item.user.name,
            "email": item.user.email,
            "last_seen_at": item.last_seen_at.isoformat(),
            "signed_in_at": item.created_at.isoformat(),
        })
        if len(users) == limit:
            break
    return users


@require_GET
def admin_dashboard(request):
    _session, error = _require_admin(request)
    if error:
        return error
    recent_users = _dashboard_recent_users()
    report_counts = ErrorReport.objects.aggregate(
        total=Count("id"),
        received=Count("id", filter=Q(status="received")),
        reviewing=Count("id", filter=Q(status="reviewing")),
        completed=Count("id", filter=Q(status="completed")),
    )
    reports = ErrorReport.objects.select_related("owner", "search_record", "handled_by").order_by("-created_at", "-id")[:6]
    searches = SearchRecord.objects.select_related("owner").order_by("-created_at", "-id")[:10]

    return JsonResponse({
        "summary": {
            "total_reports": report_counts["total"],
            "received_reports": report_counts["received"],
            "reviewing_reports": report_counts["reviewing"],
            "completed_reports": report_counts["completed"],
            "total_searches": SearchRecord.objects.count(),
            "recent_user_count": len(recent_users),
        },
        "recent_reports": [_admin_report_data(item) for item in reports],
        "recent_users": recent_users,
        "recent_searches": [{
            "id": str(item.id),
            "question": item.question,
            "audience_level": item.audience_level,
            "response_type": item.response_type,
            "user_name": item.owner.name,
            "user_email": item.owner.email,
            "created_at": item.created_at.isoformat(),
        } for item in searches],
    })


@require_GET
def admin_users(request):
    _session, error = _require_admin(request)
    if error:
        return error
    try:
        limit = min(max(int(request.GET.get("limit", 20)), 1), 100)
        offset = max(int(request.GET.get("offset", 0)), 0)
    except ValueError:
        return _error("VALIDATION_ERROR", "목록 범위를 확인해 주세요.", 422)

    active_sessions = AuthSession.objects.filter(revoked_at__isnull=True, last_seen_at__isnull=False)
    total = active_sessions.values("user_id").distinct().count()
    return JsonResponse({"items": _dashboard_recent_users(limit=limit, offset=offset), "total": total})


@require_GET
def admin_searches(request):
    _access, error = _require_admin(request)
    if error:
        return error
    try:
        limit = min(max(int(request.GET.get("limit", 20)), 1), 100)
        offset = max(int(request.GET.get("offset", 0)), 0)
    except ValueError:
        return _error("VALIDATION_ERROR", "목록 범위를 확인해 주세요.", 422)

    records = SearchRecord.objects.select_related("owner").order_by("-created_at", "-id")
    items = records[offset:offset + limit]
    return JsonResponse({
        "items": [{
            "id": str(item.id),
            "question": item.question,
            "audience_level": item.audience_level,
            "response_type": item.response_type,
            "user_name": item.owner.name,
            "user_email": item.owner.email,
            "created_at": item.created_at.isoformat(),
        } for item in items],
        "total": records.count(),
    })


@require_GET
def admin_search_detail(request, record_id):
    _access, error = _require_admin(request)
    if error:
        return error
    record = SearchRecord.objects.select_related("owner").prefetch_related("citations").filter(id=record_id).first()
    if record is None:
        return _error("RESOURCE_NOT_FOUND", "검색 기록을 찾을 수 없습니다.", 404)
    data = _record_data(record, detail=True)
    data.update({"user_name": record.owner.name, "user_email": record.owner.email})
    return JsonResponse(data)


@require_GET
def admin_error_reports(request):
    _access, error = _require_admin(request)
    if error:
        return error
    status = request.GET.get("status", "all")
    if status != "all" and status not in REPORT_STATUSES:
        return _error("VALIDATION_ERROR", "처리 상태를 확인해 주세요.", 422)
    reports = ErrorReport.objects.select_related("owner", "search_record", "handled_by")
    if status != "all":
        reports = reports.filter(status=status).order_by("-created_at", "-id")
    else:
        reports = reports.annotate(
            status_order=Case(
                When(status="received", then=Value(0)),
                When(status__in=["reviewing", "in_review"], then=Value(1)),
                When(status__in=["completed", "resolved"], then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by("status_order", "-created_at", "-id")
    return JsonResponse({"items": [_admin_report_data(item) for item in reports[:100]]})


@require_http_methods(["GET", "PATCH"])
def admin_error_report_detail(request, report_id):
    _access, error = _require_admin(request)
    if error:
        return error
    report = ErrorReport.objects.select_related("owner", "search_record", "handled_by").filter(id=report_id).first()
    if report is None:
        return _error("RESOURCE_NOT_FOUND", "오류 제보를 찾을 수 없습니다.", 404)
    if request.method == "GET":
        return JsonResponse(_admin_report_data(report, detail=True))
    payload = _payload(request)
    if payload is None:
        return _error("INVALID_REQUEST", "요청 형식이 올바르지 않습니다.")
    status = str(payload.get("status", ""))
    staff_reply = str(payload.get("staff_reply", "")).strip()
    if status not in REPORT_STATUSES or len(staff_reply) > 2000:
        return _error("VALIDATION_ERROR", "처리 상태와 담당자 답변을 확인해 주세요.", 422)
    if status == "completed" and len(staff_reply) < 10:
        return _error("VALIDATION_ERROR", "처리 완료 시 담당자 답변을 10자 이상 입력해 주세요.", 422)
    report.status = status
    report.staff_reply = staff_reply or None
    report.handled_by = None
    report.handled_at = timezone.now()
    report.save(update_fields=["status", "staff_reply", "handled_by", "handled_at", "updated_at"])
    return JsonResponse(_admin_report_data(report, detail=True))
