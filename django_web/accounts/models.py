from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """아이디는 username, 연락·로그인 식별자는 고유한 email로 관리한다."""

    email = models.EmailField("이메일", unique=True)
