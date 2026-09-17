from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Legacy AUTH_USER_MODEL declaration kept for Django migration compatibility.

    The v1 web API uses ``api.ServiceUser`` and removes the old
    ``accounts_user`` table in migration 0005. No current endpoint reads or
    writes this unmanaged model.
    """

    email = models.EmailField(unique=True)

    class Meta:
        managed = False
        db_table = "accounts_user"
