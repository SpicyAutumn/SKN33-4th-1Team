import hashlib
import json
import re
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

from .models import AuthSession, ErrorReport, SearchCitation, SearchRecord, ServiceUser
from .network_runtime import HeritageNetworkUnavailableError, build_network, build_network_for_question
from .rag_runtime import RagUnavailableError, answer as rag_answer

SESSION_COOKIE = "heritage_session"
SESSION_DAYS = 7
LEVELS = {"easy", "general", "advanced"}
REPORT_CATEGORIES = {"incorrect_fact", "citation_mismatch", "incomplete_answer", "inappropriate_content", "other"}


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
def heritage_network(request):
    document_id = str(request.GET.get("document_id", "")).strip()
    question = str(request.GET.get("question", "")).strip()
    raw_document_ids = str(request.GET.get("document_ids", "")).strip()
    document_ids = tuple(value.strip() for value in raw_document_ids.split(",") if value.strip())[:10]
    valid_id = re.compile(r"aks:[A-Za-z0-9_-]{1,64}")
    if question:
        if len(question) > 500 or any(not valid_id.fullmatch(value) for value in document_ids):
            return _error("VALIDATION_ERROR", "질문 또는 문화유산 문서 ID를 확인해 주세요.", 422)
    elif not valid_id.fullmatch(document_id):
        return _error("VALIDATION_ERROR", "문화유산 문서 ID를 확인해 주세요.", 422)
    try:
        payload = build_network_for_question(question, document_ids) if question else build_network(document_id)
    except HeritageNetworkUnavailableError:
        return _error("NETWORK_UPSTREAM_ERROR", "연관 문화유산을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", 502)
    if payload is None:
        return _error("RESOURCE_NOT_FOUND", "연결 정보를 찾지 못했습니다.", 404)
    return JsonResponse(payload)


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
        reports = ErrorReport.objects.filter(owner=session.user).select_related("search_record")[:20]
        return JsonResponse({"items": [{"id": str(item.id), "search_record_id": str(item.search_record_id), "category": item.category, "status": item.status, "question_preview": item.search_record.question[:120], "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()} for item in reports], "next_cursor": None})
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
    return JsonResponse({"id": str(report.id), "search_record_id": str(report.search_record_id), "category": report.category, "content": report.content, "status": report.status, "staff_reply": report.staff_reply, "question": report.search_record.question, "answer_preview": report.search_record.message[:160], "created_at": report.created_at.isoformat(), "updated_at": report.updated_at.isoformat()})
