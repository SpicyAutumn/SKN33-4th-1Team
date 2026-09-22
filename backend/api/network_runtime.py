"""Expose the third-project heritage graph to the Django API."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


class HeritageNetworkUnavailableError(RuntimeError):
    """Raised when the heritage graph cannot be prepared."""


def _repository_root() -> Path:
    configured = os.getenv("RAG_PROJECT_ROOT", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _graph_module():
    root = _repository_root()
    for directory in (root / "app", root / "src"):
        if not directory.is_dir():
            raise HeritageNetworkUnavailableError(f"Network source directory is missing: {directory}")
        path = str(directory)
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        import heritage_graph
    except ImportError as exc:
        raise HeritageNetworkUnavailableError("Heritage network dependencies are not installed.") from exc
    return heritage_graph


@lru_cache(maxsize=256)
def build_network(document_id: str) -> dict[str, Any] | None:
    graph = _graph_module()
    try:
        # 기본 탐색은 외부 검색/생성 서비스 및 비밀 설정에 의존하지 않는다.
        payload = _recommendations().build(document_id)
        return {**payload, "mode": "catalog"} if payload else None
    except Exception as exc:
        raise HeritageNetworkUnavailableError("Heritage network request failed.") from exc


@lru_cache(maxsize=1)
def _recommendations():
    graph = _graph_module()
    from heritage_recommendations import Recommendations
    return Recommendations(graph.catalog())


@lru_cache(maxsize=256)
def build_network_for_question(question: str, document_ids: tuple[str, ...]) -> dict[str, Any] | None:
    """Return a choice when the question or citations identify multiple subjects."""
    graph = _graph_module()
    try:
        candidates = graph.catalog().question_candidates(question, document_ids)
        if not candidates:
            return None
        if len(candidates) > 1:
            return {"mode": "catalog", "requires_selection": True,
                    "candidate_count": len(candidates),
                    "candidates": [{"document_id": entry.document_id, "title": entry.title,
                                    "field": entry.field, "item_type": entry.item_type,
                                    "keywords": list(entry.keywords[:4])}
                                   for entry in candidates[:20]]}
        return build_network(candidates[0].document_id)
    except Exception as exc:
        raise HeritageNetworkUnavailableError("Heritage network request failed.") from exc
