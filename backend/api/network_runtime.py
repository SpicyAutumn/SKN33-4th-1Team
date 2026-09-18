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


@lru_cache(maxsize=1)
def _neighbors():
    graph = _graph_module()
    try:
        return graph.build_neighbors()
    except Exception:  # The manifest-only branches still provide useful exploration.
        return None


@lru_cache(maxsize=256)
def build_network(document_id: str) -> dict[str, Any] | None:
    graph = _graph_module()
    try:
        return graph.build_map(document_id, neighbors=_neighbors())
    except Exception as exc:
        raise HeritageNetworkUnavailableError("Heritage network request failed.") from exc


@lru_cache(maxsize=256)
def build_network_for_question(question: str, document_ids: tuple[str, ...]) -> dict[str, Any] | None:
    """Resolve the user's subject first; citations are fallback candidates only."""
    graph = _graph_module()
    try:
        root = graph.catalog().resolve_question(question, document_ids)
        if root is None:
            return None
        return graph.build_map(root.document_id, neighbors=_neighbors())
    except Exception as exc:
        raise HeritageNetworkUnavailableError("Heritage network request failed.") from exc
