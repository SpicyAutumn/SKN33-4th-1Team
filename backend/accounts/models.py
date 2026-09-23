from django.db import models


class User(models.Model):
    """Legacy AUTH_USER_MODEL declaration kept for Django migration compatibility.

    The v1 web API uses ``api.ServiceUser`` and removes the old
    ``accounts_user`` table in migration 0005. No current endpoint reads or
    writes this unmanaged model.
    """

    # Only the fields read by migrations 0002-0004 are retained. This is not
    # a runtime authentication model and must not pull in auth permissions.
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "accounts_user"
