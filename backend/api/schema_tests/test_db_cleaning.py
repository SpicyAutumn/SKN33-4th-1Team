import hashlib
import json
import secrets
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from api.models import AuthSession, ErrorReport, SearchRecord, ServiceUser
from api.views import SESSION_COOKIE


class ErrorReportApiTests(TestCase):
    def test_only_service_tables_and_migration_history_remain(self):
        from django.apps import apps
        from django.db import connection

        self.assertFalse(apps.is_installed("django.contrib.auth"))
        self.assertFalse(apps.is_installed("django.contrib.contenttypes"))
        tables = set(connection.introspection.table_names()) - {"django_migrations"}
        self.assertEqual(tables, {
            "users", "auth_sessions", "search_records", "search_citations", "search_results",
            "error_reports", "error_report_types", "error_report_quotes",
        })

    def setUp(self):
        self.user = ServiceUser.objects.create(
            email="report-test@example.com",
            name="제보 테스트",
            password_hash="not-used-in-this-test",
        )
        token = secrets.token_urlsafe(32)
        AuthSession.objects.create(
            user=self.user,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.cookies[SESSION_COOKIE] = token

        sentence = "다보탑은 통일신라 시대에 건립된 석탑이다."
        self.answer = f"{sentence} {sentence}"
        self.record = SearchRecord.objects.create(
            owner=self.user,
            rag_request_id="error-report-test-request",
            question="불국사 다보탑에 대해 알려줘",
            audience_level="general",
            response_type="answered",
            message=self.answer,
        )

    def test_registers_multiple_types_and_repeated_quotes(self):
        sentence = "다보탑은 통일신라 시대에 건립된 석탑이다."
        first_start = self.answer.index(sentence)
        second_start = self.answer.rindex(sentence)
        response = self.client.post(
            "/api/v1/me/error-reports",
            data=json.dumps({
                "search_record_id": str(self.record.id),
                "categories": ["incorrect_fact", "citation_mismatch"],
                "content": "",
                "selected_quotes": [
                    {"text": sentence, "start_offset": first_start, "end_offset": first_start + len(sentence)},
                    {"text": sentence, "start_offset": second_start, "end_offset": second_start + len(sentence)},
                ],
            }),
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["categories"], ["incorrect_fact", "citation_mismatch"])
        self.assertEqual(len(data["selected_quotes"]), 2)
        self.assertNotEqual(data["selected_quotes"][0]["start_offset"], data["selected_quotes"][1]["start_offset"])

        report = ErrorReport.objects.get(id=data["id"])
        self.assertEqual(list(report.types.values_list("code", flat=True)), ["incorrect_fact", "citation_mismatch"])
        self.assertEqual(report.selected_quotes.count(), 2)

        detail = self.client.get(f"/api/v1/me/error-reports/{report.id}", HTTP_HOST="localhost")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()["selected_quotes"]), 2)

    def post_report(self, **fields):
        return self.client.post(
            "/api/v1/me/error-reports",
            {"search_record_id": str(self.record.id),
             "category": "incorrect_fact", "content": "Please check this answer.", **fields},
            content_type="application/json",
        )

    def test_legacy_client_uses_child_type_without_category_column(self):
        from django.db import connection

        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, "error_reports")
        self.assertNotIn("category", [column.name for column in columns])
        response = self.post_report()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["category"], "incorrect_fact")
        self.assertEqual(response.json()["categories"], ["incorrect_fact"])
        listing = self.client.get("/api/v1/me/error-reports").json()["items"]
        self.assertEqual(listing[0]["content_preview"], "Please check this answer.")

    def test_invalid_quotes_and_types_do_not_create_reports(self):
        cases = [
            {"categories": []},
            {"categories": ["unknown"]},
            {"selected_quotes": [{"text": "fabricated quote"}]},
            {"selected_quotes": [{"text": self.answer, "start_offset": True, "end_offset": len(self.answer)}]},
            {"selected_quotes": [{"text": self.answer, "start_offset": 1, "end_offset": len(self.answer)}]},
            {"selected_quotes": [{"text": self.answer}] * 6},
            {"category": "other", "content": "", "selected_quotes": [{"text": self.answer}]},
        ]
        for fields in cases:
            with self.subTest(fields=fields):
                self.assertEqual(self.post_report(**fields).status_code, 422)
        self.assertEqual(ErrorReport.objects.count(), 0)

    def test_report_cannot_target_another_users_answer(self):
        other = ServiceUser.objects.create(email="other@example.com", name="Other", password_hash="unused")
        self.record.owner = other
        self.record.save(update_fields=["owner"])
        self.assertEqual(self.post_report().status_code, 404)

    def test_admin_reads_types_quotes_and_updates_report(self):
        response = self.post_report(categories=["incorrect_fact", "citation_mismatch"],
                                    selected_quotes=[{"text": self.answer}])
        self.assertEqual(response.status_code, 201)
        report_id = response.json()["id"]
        from django.conf import settings

        login = self.client.post("/api/v1/admin/login", {"password": settings.ADMIN_DASHBOARD_PASSWORD},
                                 content_type="application/json")
        self.assertEqual(login.status_code, 200)
        for path in ("/api/v1/admin/dashboard", "/api/v1/admin/error-reports"):
            self.assertEqual(self.client.get(path).status_code, 200)
        path = f"/api/v1/admin/error-reports/{report_id}"
        detail = self.client.get(path).json()
        self.assertEqual(detail["categories"], ["incorrect_fact", "citation_mismatch"])
        self.assertEqual(detail["selected_quotes"][0]["text"], self.answer)
        updated = self.client.patch(path, {"status": "completed", "staff_reply": "We checked and corrected it."},
                                    content_type="application/json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "completed")

    def test_signup_login_and_logout_do_not_need_django_session(self):
        self.client.cookies.clear()
        response = self.client.post("/api/v1/auth/signup", {
            "name": "New", "email": "new@example.com", "password": "test-password-123",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        response = self.client.post("/api/v1/auth/login", {
            "email": "new@example.com", "password": "test-password-123",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_account_deletion_removes_results_and_report_children(self):
        from django.contrib.auth.hashers import make_password
        from api.models import ErrorReportQuote, ErrorReportType, SearchResult

        self.user.password_hash = make_password("delete-test-password")
        self.user.save(update_fields=["password_hash"])
        SearchResult.objects.create(id=self.record.id, owner=self.user, payload={"message": self.answer})
        self.assertEqual(self.post_report(selected_quotes=[{"text": self.answer}]).status_code, 201)
        response = self.client.delete("/api/v1/me", {
            "current_password": "delete-test-password", "confirmation": "탈퇴",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 204)
        for model in (ServiceUser, AuthSession, SearchRecord, SearchResult,
                      ErrorReport, ErrorReportType, ErrorReportQuote):
            self.assertEqual(model.objects.count(), 0, model.__name__)
