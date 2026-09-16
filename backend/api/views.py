import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User
from .rag_runtime import RagUnavailableError, answer as rag_answer


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
    if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
        return _error("이미 사용 중인 사용자명 또는 이메일입니다.", 409)
    user = User.objects.create_user(username=username, email=email, password=password)
    login(request, user)
    return JsonResponse({"id": user.id, "username": user.username, "email": user.email}, status=201)


@csrf_exempt
@require_POST
def login_view(request):
    payload = _payload(request)
    if payload is None:
        return _error("요청 형식이 올바르지 않습니다.")
    identity = str(payload.get("identity", "")).strip()
    password = str(payload.get("password", ""))
    user = User.objects.filter(email__iexact=identity).first() or User.objects.filter(username=identity).first()
    authenticated = authenticate(request, username=user.username, password=password) if user else None
    if authenticated is None:
        return _error("이메일 또는 비밀번호를 확인해 주세요.", 401)
    login(request, authenticated)
    return JsonResponse({"id": authenticated.id, "username": authenticated.username, "email": authenticated.email})


@csrf_exempt
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"user": None})
    return JsonResponse({"user": {"id": request.user.id, "username": request.user.username, "email": request.user.email}})


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
