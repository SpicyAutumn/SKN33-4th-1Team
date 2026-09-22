import importlib.util
from pathlib import Path

import pytest


def load_server():
    path = Path(__file__).parents[1] / "scripts" / "integration" / "server.py"
    spec = importlib.util.spec_from_file_location("integration_server", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_validate_payload_accepts_ordered_immutable_revisions():
    server = load_server()
    sha = "a" * 40
    assert server.validate_payload({"main_sha": sha, "prs": [{"number": 4, "sha": sha}]}) == (sha, [(4, sha)])


@pytest.mark.parametrize("payload", [
    {"main_sha": "bad", "prs": []},
    {"main_sha": "a" * 40, "prs": [{"number": 2, "sha": "a" * 40}, {"number": 2, "sha": "b" * 40}]},
    {"main_sha": "a" * 40, "prs": [{"number": 1, "sha": "not-a-sha"}]},
])
def test_validate_payload_rejects_untrusted_or_ambiguous_revisions(payload):
    server = load_server()
    with pytest.raises(ValueError):
        server.validate_payload(payload)


def test_api_environment_excludes_database_and_django_values(tmp_path):
    server = load_server()
    env = tmp_path / "test-api.env"
    env.write_text("OPENAI_API_KEY=allowed\nMYSQL_PASSWORD=blocked\nDJANGO_SECRET_KEY=blocked\n")
    assert server.parse_api_environment(env) == {"OPENAI_API_KEY": "allowed"}


def test_credentials_are_stable_across_releases(tmp_path, monkeypatch):
    server = load_server()
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "command", lambda *a, **kw: "")
    (tmp_path / "test-api.env").write_text("MYSQL_PASSWORD=must-not-use\n")
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir(); second.mkdir()
    server.configure_release(first, "127.0.0.1")
    server.configure_release(second, "127.0.0.1")
    assert (first / "mysql.env").read_text() == (second / "mysql.env").read_text()
    assert "must-not-use" not in (second / "app.env").read_text()
    assert server.compose_config(second, "127.0.0.1")["volumes"]["db"]["name"] == "heritage-integration_db"


def test_existing_release_credentials_are_adopted(tmp_path, monkeypatch):
    server = load_server()
    monkeypatch.setattr(server, "ROOT", tmp_path)
    old = tmp_path / "old"; old.mkdir()
    new = tmp_path / "new"; new.mkdir()
    (tmp_path / "test-api.env").write_text("")
    content = "MYSQL_DATABASE=integration\nMYSQL_USER=integration\nMYSQL_PASSWORD=old\nMYSQL_ROOT_PASSWORD=root-old\n"
    (old / "mysql.env").write_text(content)
    monkeypatch.setattr(server, "active_release", lambda: old)
    server.configure_release(new, "127.0.0.1")
    assert (new / "mysql.env").read_text() == content


def test_orphan_volume_without_credentials_is_not_reinitialized(tmp_path, monkeypatch):
    server = load_server()
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "command", lambda *a, **kw: "heritage-integration_db")
    (tmp_path / "test-api.env").write_text("")
    with pytest.raises(RuntimeError, match="no credentials"):
        server.configure_release(tmp_path, "127.0.0.1")


def test_stop_preserves_volume_and_active_pointer(tmp_path, monkeypatch):
    server = load_server()
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "active_release", lambda: tmp_path)
    (tmp_path / "active.json").write_text("{}")
    calls = []
    monkeypatch.setattr(server, "compose", lambda *a: calls.append(a))
    server.stop_active()
    assert calls == [(tmp_path, "down", "--remove-orphans")]
    assert (tmp_path / "active.json").exists()


def test_failed_migration_is_not_retried_and_sets_review_marker(tmp_path, monkeypatch):
    import subprocess
    server = load_server()
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "backup_database", lambda release: None)
    calls = []
    def compose(*args):
        calls.append(args)
        if "run" in args:
            raise subprocess.CalledProcessError(1, "migration")
    monkeypatch.setattr(server, "compose", compose)
    with pytest.raises(subprocess.CalledProcessError):
        server.start_release(tmp_path, "127.0.0.1")
    assert len([c for c in calls if "run" in c]) == 1
    assert (tmp_path / "database-review-required.json").exists()


def test_no_preview_prs_still_deploys_main(tmp_path, monkeypatch):
    import base64
    import json
    import sys
    from types import SimpleNamespace

    server = load_server()
    monkeypatch.setattr(server, "ROOT", tmp_path)
    (tmp_path / ".test-server").touch()
    (tmp_path / "test-api.env").touch()
    (tmp_path / "server.json").write_text('{"public_ip":"127.0.0.1"}')
    (tmp_path / "data").mkdir()
    (tmp_path / "data/aks_bm25_v1.sqlite3").touch()
    (tmp_path / "data/aks_article_medias.jsonl").touch()
    payload = base64.b64encode(json.dumps({"main_sha": "a" * 40, "prs": []}).encode()).decode()
    monkeypatch.setattr(sys, "argv", ["server.py", payload])
    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(LOCK_EX=1, flock=lambda *a: None))
    calls = []
    monkeypatch.setattr(server, "create_source", lambda release, sha, prs: calls.append((sha, prs)))
    monkeypatch.setattr(server, "configure_release", lambda *a: None)
    monkeypatch.setattr(server, "compose", lambda *a: None)
    monkeypatch.setattr(server, "start_release", lambda *a: calls.append("started"))
    server.main()
    assert calls == [("a" * 40, []), "started"]
    assert json.loads((tmp_path / "active.json").read_text())["prs"] == []
