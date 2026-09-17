"""Django API에서 기존 RAG 실행 계층을 안전하게 호출한다."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


class RagUnavailableError(RuntimeError):
    """필수 설정이나 RAG 의존성이 준비되지 않은 경우."""


def _repository_root() -> Path:
    configured = os.getenv("RAG_PROJECT_ROOT", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _retrieval_module():
    root = _repository_root()
    for directory in (root / "app", root / "src"):
        if not directory.is_dir():
            raise RagUnavailableError(f"RAG source directory is missing: {directory}")
        path = str(directory)
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        import rag_client
        import retrieval
    except ImportError as exc:
        raise RagUnavailableError("RAG dependencies are not installed.") from exc

    return rag_client, retrieval


def answer(question: str, *, audience_level: str) -> dict[str, Any]:
    rag_client, retrieval = _retrieval_module()
    missing = rag_client.missing_env()
    if missing:
        raise RagUnavailableError("RAG environment is not configured: " + ", ".join(missing))

    try:
        execution = retrieval.answer(question, audience_level=audience_level)
    except Exception as exc:  # The API view keeps infrastructure detail out of the browser response.
        raise RagUnavailableError("RAG request failed.") from exc

    response = execution.get("response") if isinstance(execution, dict) else None
    if not isinstance(response, dict):
        raise RagUnavailableError("RAG returned an invalid response.")
    return {**response, "demo": False}
