from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Member(models.Model):
    """Application-owned member records, separate from the instructor table."""

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "heritage_members"
        ordering = ["-created_at"]

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)

    def public_data(self) -> dict:
        return {"id": self.id, "username": self.username, "email": self.email}
