import json
import os
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import RequestFactory, override_settings

from api.views import ADMIN_SESSION_COOKIE, admin_dashboard, admin_login, admin_session


@override_settings(ADMIN_DASHBOARD_PASSWORD="test-admin-password")
class AdminDashboardAccessTest(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_dashboard_requires_admin_password_before_database_access(self):
        response = admin_dashboard(self.factory.get("/api/v1/admin/dashboard"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"]["code"], "ADMIN_PASSWORD_REQUIRED")

    def test_password_creates_a_session_that_admin_session_recognizes(self):
        login_response = admin_login(self.factory.post(
            "/api/v1/admin/login",
            data=json.dumps({"password": "test-admin-password"}),
            content_type="application/json",
        ))
        request = self.factory.get("/api/v1/admin/session")
        request.COOKIES[ADMIN_SESSION_COOKIE] = login_response.cookies[ADMIN_SESSION_COOKIE].value
        session_response = admin_session(request)

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(session_response.status_code, 200)
        self.assertTrue(json.loads(session_response.content)["authenticated"])

    def test_wrong_password_is_rejected(self):
        response = admin_login(self.factory.post(
            "/api/v1/admin/login",
            data=json.dumps({"password": "wrong-password"}),
            content_type="application/json",
        ))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"]["code"], "INVALID_ADMIN_PASSWORD")
