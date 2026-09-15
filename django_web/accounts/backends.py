from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """아이디 또는 이메일 어느 쪽으로도 로그인할 수 있게 한다."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get("email") or "").strip()
        if not identifier or not password:
            return None

        user_model = get_user_model()
        try:
            user = user_model.objects.get(Q(username=identifier) | Q(email__iexact=identifier))
        except user_model.DoesNotExist:
            return None
        return user if user.check_password(password) and self.user_can_authenticate(user) else None
