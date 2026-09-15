import json

from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import LoginForm, SignUpForm


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("heritage:mypage")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("heritage:mypage")
    return render(request, "accounts/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("heritage:mypage")
    form = LoginForm(request, request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(request.POST.get("next") or "heritage:mypage")
    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("heritage:home")


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _user_payload(user):
    return {"id": user.pk, "username": user.username, "email": user.email}


@require_GET
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})


@require_POST
def signup_api(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON 형식이 올바르지 않습니다."}, status=400)
    form = SignUpForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    user = form.save()
    login(request, user)
    return JsonResponse({"user": _user_payload(user)}, status=201)


@require_POST
def login_api(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON 형식이 올바르지 않습니다."}, status=400)
    form = LoginForm(request, data)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    user = form.get_user()
    login(request, user)
    return JsonResponse({"user": _user_payload(user)})


@require_POST
def logout_api(request):
    logout(request)
    return JsonResponse({"detail": "로그아웃했습니다."})


@require_GET
def me_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "로그인이 필요합니다."}, status=401)
    return JsonResponse({"user": _user_payload(request.user)})
