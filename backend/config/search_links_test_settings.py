"""Isolated SQLite tests; never access production settings or credentials.

Historical migrations contain MySQL-only cleanup SQL. Build the current model
schema for API integration tests; validate the new migration separately.
"""
from .test_settings import *
MIGRATION_MODULES = {"api": None, "accounts": None, "auth": None, "contenttypes": None}
SESSION_COOKIE_SECURE = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
MIDDLEWARE = ["django.middleware.csrf.CsrfViewMiddleware"]
ADMIN_DASHBOARD_PASSWORD = "test-only"
