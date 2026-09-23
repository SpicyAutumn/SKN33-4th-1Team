"""Offline API unit tests: never load production settings or .env.

SimpleTestCase blocks database queries. SQLite is configured only so Django can
load model metadata without requiring a MySQL driver or server.
"""

SECRET_KEY = "offline-unit-test-only"
INSTALLED_APPS = [
    "accounts",
    "api",
]
AUTH_USER_MODEL = "accounts.User"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "api.urls"
USE_TZ = True
