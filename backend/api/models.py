from django.conf import settings
from django.db import models


class SearchHistory(models.Model):
    """A logged-in member's question history for the web home screen."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="user_id",
        on_delete=models.CASCADE,
        related_name="search_histories",
    )
    question = models.CharField(max_length=500)
    audience_level = models.CharField(max_length=20)
    response_type = models.CharField(max_length=40, default="answered")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_history"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "created_at"], name="search_hist_user_created_idx")]
