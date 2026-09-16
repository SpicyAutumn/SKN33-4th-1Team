from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Existing django_project4.accounts_user table mapping.

    The team database already contains this Django-style table.  It is marked
    unmanaged so the MVP never tries to recreate or alter it automatically.
    Future schema changes must be added through reviewed migrations.
    """

    email = models.EmailField(unique=True)

    class Meta:
        managed = False
        db_table = "accounts_user"
