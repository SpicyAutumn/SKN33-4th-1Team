import hashlib
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone

from api.models import AuthSession, SearchRecord, SearchResult, ServiceUser
from api.search_links import GUEST_COOKIE


class SearchLinksTest(TestCase):
    def setUp(self):
        self.answer = {"request_id": "REQ-test", "interaction_id": "internal-session",
                       "response_type": "answered", "message": "경복궁에 대한 답변",
                       "summary": "요약", "citations": [], "media": [{"images": []}],
                       "debug": "must never be shared"}
        mock = patch("api.views.rag_answer", return_value=self.answer)
        self.rag = mock.start()
        self.addCleanup(mock.stop)

    def search(self, client=None):
        response = (client or self.client).post("/v1/searches", {"question": "경복궁", "audience_level": "general"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        return data, "/v1/searches/" + data["search_result_id"]

    def login(self, client, email):
        user = ServiceUser.objects.create(email=email, name="Private name", password_hash="unused")
        token = uuid.uuid4().hex
        AuthSession.objects.create(user=user, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=timezone.now() + timedelta(days=1))
        client.cookies["heritage_session"] = token
        return user

    def test_guest_refresh_preserves_exact_answer_without_new_generation(self):
        data, path = self.search()
        self.assertIsNone(data["search_record_id"])
        self.assertTrue(self.client.cookies[GUEST_COOKIE]["httponly"])
        restored = self.client.get(path)
        self.assertEqual(restored.status_code, 200)
        for key in ("summary", "message", "media", "citations", "question", "audience_level"):
            self.assertEqual(restored.json()[key], data[key])
        self.assertEqual(self.rag.call_count, 1)
        self.assertIn("no-store", restored["Cache-Control"])

    def test_guest_result_cannot_be_read_or_shared_by_other_browser(self):
        _, path = self.search()
        stranger = Client()
        self.assertEqual(stranger.get(path).status_code, 404)
        self.assertEqual(stranger.post(path + "/share").status_code, 404)
        self.assertIsNone(SearchResult.objects.get().share_token)

    def test_explicit_sharing_is_public_stable_and_redacted(self):
        data, path = self.search()
        link = self.client.post(path + "/share").json()["share_path"]
        self.assertNotIn(data["search_result_id"], link)
        self.assertEqual(self.client.post(path + "/share").json()["share_path"], link)
        response = Client().get("/v1/shared-searches/" + link.split("/")[-1])
        self.assertEqual(response.status_code, 200)
        public = response.json()
        for key in ("owner", "email", "guest_token_hash", "search_record_id", "search_result_id", "request_id", "interaction_id", "debug", "id"):
            self.assertNotIn(key, public)
        self.assertEqual(public["message"], data["message"])
        self.assertEqual(public["summary"], data["summary"])
        self.assertTrue(public["shared"])
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(Client().get(path).status_code, 404)
        self.assertEqual(self.rag.call_count, 1)

    def test_member_result_requires_same_user(self):
        owner = self.login(self.client, "owner@example.com")
        data, path = self.search()
        self.assertEqual(data["search_record_id"], data["search_result_id"])
        self.assertEqual(SearchRecord.objects.get().owner, owner)
        self.assertEqual(self.client.get(path).status_code, 200)
        other = Client()
        self.login(other, "other@example.com")
        self.assertEqual(other.get(path).status_code, 404)
        self.assertEqual(other.post(path + "/share").status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_old_record_can_be_restored_and_explicitly_shared(self):
        owner = self.login(self.client, "old@example.com")
        record = SearchRecord.objects.create(owner=owner, rag_request_id="legacy", question="옛 질문", audience_level="general", response_type="answered", message="옛 답변")
        path = f"/v1/searches/{record.id}"
        self.assertEqual(self.client.get(path).json()["message"], "옛 답변")
        self.assertEqual(SearchResult.objects.count(), 0)
        share_path = self.client.post(path + "/share").json()["share_path"]
        public = Client().get("/v1/shared-searches/" + share_path.split("/")[-1]).json()
        self.assertEqual(public["message"], "옛 답변")
        self.rag.assert_not_called()

    def test_unknown_and_invalid_urls(self):
        for path in (f"/v1/searches/{uuid.uuid4()}", f"/v1/shared-searches/{uuid.uuid4()}", "/v1/searches/not-a-uuid"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_sharing_requires_post_and_csrf(self):
        _, path = self.search()
        self.assertEqual(self.client.get(path + "/share").status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.cookies = self.client.cookies.copy()
        self.assertEqual(strict.post(path + "/share").status_code, 403)

    def test_rag_error_does_not_create_result(self):
        from api.rag_runtime import RagUnavailableError
        self.rag.side_effect = RagUnavailableError("offline")
        response = self.client.post("/v1/searches", {"question": "경복궁"}, content_type="application/json")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(SearchResult.objects.count(), 0)
