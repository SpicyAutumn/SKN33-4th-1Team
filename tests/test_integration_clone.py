import importlib.util
import json
from pathlib import Path

import pytest


def load_clone():
    path = Path(__file__).parents[1] / "scripts/integration/clone_database.py"
    spec = importlib.util.spec_from_file_location("clone_database", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_user_and_result_credentials_are_invalidated():
    clone = load_clone()
    row = clone.sanitize("users", {"id": "a" * 32, "email": "real@example.com",
                                  "name": "Real Name", "password_hash": "secret"}, set())
    assert row["email"].endswith("@example.invalid")
    assert row["password_hash"].startswith("!")
    assert row["name"] == "Test member"
    result = clone.sanitize("search_results", {"id": "b", "owner_id": None,
        "guest_token_hash": "old", "share_token": "public-secret", "payload": json.dumps({
            "message": "private answer", "question": "private question", "audience_level": "general",
            "citations": [{"content": "private content"}], "private-key": "sensitive",
        })}, {"payload"})
    assert result["share_token"] is None and result["guest_token_hash"] != "old"
    assert "private" not in result["payload"] and "sensitive" not in result["payload"]
    assert json.loads(result["payload"])["audience_level"] == "general"


def test_quote_offsets_remain_valid_after_scrubbing():
    clone = load_clone()
    answer = "앞🙂 반복 문구"
    text = answer[2:]
    record = clone.sanitize("search_records", {"message": answer}, set())
    quote = clone.sanitize("error_report_quotes", {"text": text, "start_offset": 2, "end_offset": len(answer)}, set())
    assert record["message"][quote["start_offset"]:quote["end_offset"]] == quote["text"]


@pytest.mark.parametrize("values", [
    {"MYSQL_HOST": "production", "MYSQL_DATABASE": "integration", "INTEGRATION_DATABASE": "1"},
    {"MYSQL_HOST": "127.0.0.1", "MYSQL_DATABASE": "django_project4", "INTEGRATION_DATABASE": "1"},
    {"MYSQL_HOST": "db", "MYSQL_DATABASE": "integration"},
])
def test_restore_rejects_non_test_targets_before_connecting(values, monkeypatch):
    clone = load_clone()
    monkeypatch.setattr(clone, "connect", lambda *_: pytest.fail("must not connect"))
    with pytest.raises(RuntimeError, match="restricted"):
        clone.restore_snapshot(Path("not-read.json"), values)


def test_restore_rejects_nonempty_target(tmp_path, monkeypatch):
    clone = load_clone()
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps({"format": 1, "sanitized": True, "tables": {}}))
    class DB:
        def cursor(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql): assert sql == "SHOW TABLES"
        def fetchall(self): return [("users",)]
        def close(self): pass
    monkeypatch.setattr(clone, "connect", lambda *_: DB())
    with pytest.raises(RuntimeError, match="empty"):
        clone.restore_snapshot(path, {"MYSQL_HOST": "db", "MYSQL_DATABASE": "integration", "INTEGRATION_DATABASE": "1"})
