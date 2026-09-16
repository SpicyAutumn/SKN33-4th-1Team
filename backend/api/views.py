import json

from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Member
from .rag_runtime import RagUnavailableError, answer as rag_answer


MEMBER_SESSION_KEY = "heritage_member_id"


def _payload(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _error(message, status=400):
    return JsonResponse({"detail": message}, status=status)


@require_GET
def health(_request):
    return JsonResponse({"status": "ok", "chat_mode": "rag"})


@csrf_exempt
@require_POST
def signup(request):
    payload = _payload(request)
    if payload is None:
        return _error("요청 형식이 올바르지 않습니다.")
    username = str(payload.get("username", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if not username or not email or len(password) < 8:
        return _error("사용자명, 이메일, 8자 이상 비밀번호를 입력해 주세요.")
    member = Member(username=username, email=email)
    member.set_password(password)
    try:
        member.save()
    except IntegrityError:
        return _error("이미 사용 중인 사용자명 또는 이메일입니다.", 409)
    request.session.cycle_key()
    request.session[MEMBER_SESSION_KEY] = member.id
    return JsonResponse(member.public_data(), status=201)


@csrf_exempt
@require_POST
def login_view(request):
    payload = _payload(request)
    if payload is None:
        return _error("요청 형식이 올바르지 않습니다.")
    identity = str(payload.get("identity", "")).strip()
    password = str(payload.get("password", ""))
    member = Member.objects.filter(email__iexact=identity).first() or Member.objects.filter(username=identity).first()
    if member is None or not member.check_password(password):
        return _error("이메일 또는 비밀번호를 확인해 주세요.", 401)
    request.session.cycle_key()
    request.session[MEMBER_SESSION_KEY] = member.id
    return JsonResponse(member.public_data())


@csrf_exempt
@require_POST
def logout_view(request):
    request.session.flush()
    return JsonResponse({"ok": True})


@require_GET
def me(request):
    member_id = request.session.get(MEMBER_SESSION_KEY)
    member = Member.objects.filter(id=member_id).first() if member_id else None
    if member is None:
        return JsonResponse({"user": None})
    return JsonResponse({"user": member.public_data()})


@csrf_exempt
@require_POST
def chat(request):
    """Run the existing RAG service with the web request's selected explanation level."""
    payload = _payload(request)
    if payload is None:
        return _error("요청 형식이 올바르지 않습니다.")
    question = str(payload.get("question", "")).strip()
    audience_level = str(payload.get("audience_level", "easy"))
    if not question:
        return _error("질문을 입력해 주세요.")
    if audience_level not in {"easy", "general", "advanced"}:
        return _error("설명 수준이 올바르지 않습니다.")
    try:
        return JsonResponse(rag_answer(question, audience_level=audience_level))
    except RagUnavailableError:
        return _error("지금은 자료를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", 503)
