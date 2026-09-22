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
