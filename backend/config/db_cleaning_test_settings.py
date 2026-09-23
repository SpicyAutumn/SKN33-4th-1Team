"""Isolated schema/API tests using current models and an in-memory database.

Historical MySQL migrations are exercised separately on a disposable MySQL DB.
This module deliberately does not load .env or production database settings.
"""

from .test_settings import *  # noqa: F403

ROOT_URLCONF = "config.urls"
MIGRATION_MODULES = {"api": None, "accounts": None}
ALLOWED_HOSTS = ["testserver", "localhost"]
SESSION_COOKIE_SECURE = False
ADMIN_DASHBOARD_PASSWORD = "schema-test-admin"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
