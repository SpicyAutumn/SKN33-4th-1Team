import hashlib
import json
import secrets
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import AuthSession, ErrorReport, SearchRecord, ServiceUser
from .views import SESSION_COOKIE


class ErrorReportApiTests(TestCase):
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
