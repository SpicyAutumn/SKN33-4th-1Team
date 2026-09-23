"""Exercise real test-DB writes through Django views, then roll everything back.

Run inside the test backend: python /workspace/scripts/integration/smoke_cleanup.py
RAG is stubbed so this verifies persistence/auth independently of external AI.
"""
import os
import secrets
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.db import connection, transaction
from django.test import Client, override_settings

db = connection.settings_dict
allowed = ((db["HOST"] == "db" and db["NAME"] == "integration" and os.getenv("INTEGRATION_DATABASE") == "1")
           or (db["HOST"] == "127.0.0.1" and str(db["PORT"]) == "33316" and db["NAME"].startswith("mk_cleaning_verify_")))
if not allowed:
    raise RuntimeError("Smoke writes are allowed only in the isolated test database")

expected = {"users", "auth_sessions", "search_records", "search_citations", "search_results",
            "error_reports", "error_report_types", "error_report_quotes", "django_migrations"}
assert set(connection.introspection.table_names()) == expected


def expect(response, status):
    assert response.status_code == status, (response.status_code, response.content[:300])
    return response.json() if response.content else None


with override_settings(ALLOWED_HOSTS=["testserver"], SESSION_COOKIE_SECURE=False,
                       ADMIN_DASHBOARD_PASSWORD="isolated-smoke-admin"), transaction.atomic():
    nonce = secrets.token_hex(8)
    client = Client()
    email = f"cleanup-{nonce}@example.invalid"
    password = "cleanup-smoke-password-123"
    expect(client.post("/api/v1/auth/signup", {"email": email, "name": "Cleanup smoke", "password": password}, content_type="application/json"), 201)
    expect(client.get("/api/v1/auth/me"), 200)
    expect(client.post("/api/v1/auth/logout"), 204)
    expect(client.get("/api/v1/auth/me"), 401)
    expect(client.post("/api/v1/auth/login", {"email": email, "password": password}, content_type="application/json"), 200)
    answer = "A test answer for a historical site."
    response = {"request_id": nonce, "response_type": "answered", "message": answer, "citations": [{
        "chunk_id": "smoke-chunk", "document_id": "smoke-document", "title": "Smoke source", "source_url": "https://example.invalid/source",
        "section": "test", "retrieval_rank": 1, "content": "Source passage."}]}
    with patch("api.views.rag_answer", return_value=response):
        result = expect(client.post("/api/v1/searches", {"question": "Test question", "audience_level": "general"}, content_type="application/json"), 200)
    expect(client.get("/api/v1/me/searches"), 200)
    expect(client.get("/api/v1/me/searches/" + result["search_record_id"]), 200)
    path = "/api/v1/searches/" + result["search_result_id"]
    expect(client.get(path), 200)
    expect(Client().get(path), 404)
    share = expect(client.post(path + "/share"), 200)["share_path"].split("/")[-1]
    expect(Client().get("/api/v1/shared-searches/" + share), 200)
    report = expect(client.post("/api/v1/me/error-reports", {
        "search_record_id": result["search_record_id"], "category": "incorrect_fact", "content": "Test report details.",
        "selected_quotes": [{"text": answer, "start_offset": 0, "end_offset": len(answer)}],
    }, content_type="application/json"), 201)
    assert report["category"] == "incorrect_fact" and len(report["selected_quotes"]) == 1
    expect(client.get("/api/v1/me/error-reports"), 200)
    expect(client.get("/api/v1/me/error-reports/" + report["id"]), 200)
    admin = Client()
    expect(admin.get("/api/v1/admin/dashboard"), 401)
    expect(admin.post("/api/v1/admin/login", {"password": settings.ADMIN_DASHBOARD_PASSWORD}, content_type="application/json"), 200)
    expect(admin.get("/api/v1/admin/dashboard"), 200)
    expect(admin.get("/api/v1/admin/error-reports"), 200)
    report_path = "/api/v1/admin/error-reports/" + report["id"]
    expect(admin.get(report_path), 200)
    expect(admin.patch(report_path, {"status": "completed", "staff_reply": "Checked and corrected."}, content_type="application/json"), 200)
    guest = Client()
    with patch("api.views.rag_answer", return_value={**response, "request_id": nonce + "-guest"}):
        guest_result = expect(guest.post("/api/v1/searches", {"question": "Guest question", "audience_level": "general"}, content_type="application/json"), 200)
    expect(guest.get("/api/v1/searches/" + guest_result["search_result_id"]), 200)
    expect(Client().get("/api/v1/searches/" + guest_result["search_result_id"]), 404)
    expect(client.delete("/api/v1/me", {"current_password": password, "confirmation": "탈퇴"}, content_type="application/json"), 204)
    transaction.set_rollback(True)

print("CLEANUP_SMOKE_OK: signup/login/logout/history/citations/private/shared/guest/report/admin/delete; all writes rolled back")
