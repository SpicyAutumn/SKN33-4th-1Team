"""Test helpers use existing repository fixtures; no network is permitted."""
from pathlib import Path
import socket
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network prohibited in experiment tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    for name in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2"):
        monkeypatch.setenv(name, "false")
