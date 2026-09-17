"""검색 결과의 문서 ID를 공공누리 미디어 JSONL과 연결한다."""

from __future__ import annotations

import json
import os
import threading
from html import unescape
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


KOGL_TYPES = {"KOGL1", "KOGL2", "KOGL3", "KOGL4"}


def _text(value: Any) -> str:
    return unescape(value).strip() if isinstance(value, str) else ""


def _default_media_path() -> Path:
    configured = os.getenv("AKS_MEDIA_JSONL_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "processed" / "aks_article_medias.jsonl"


class MediaCatalog:
    """JSONL 전체를 메모리에 올리지 않고 문서별 파일 위치만 색인한다."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._offsets: dict[str, int] | None = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.path.is_file()

    def _ensure_index(self) -> dict[str, int]:
        if self._offsets is not None:
            return self._offsets
        with self._lock:
            if self._offsets is not None:
                return self._offsets
            offsets: dict[str, int] = {}
            if self.available:
                with self.path.open("rb") as stream:
                    while True:
                        offset = stream.tell()
                        raw_line = stream.readline()
                        if not raw_line:
                            break
                        try:
                            row = json.loads(raw_line)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        document_id = row.get("document_id")
                        if isinstance(document_id, str) and document_id:
                            offsets[document_id] = offset
            self._offsets = offsets
            return offsets

    @staticmethod
    def _clean_row(row: dict[str, Any]) -> dict[str, Any] | None:
        document_id = row.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            return None
        images = []
        for image in row.get("images") or []:
            if not isinstance(image, dict):
                continue
            url = _text(image.get("url"))
            kogl_type = _text(image.get("kogl_type"))
            if not url or kogl_type not in KOGL_TYPES:
                continue
            images.append({
                "mid": _text(image.get("mid")),
                "role": _text(image.get("role")),
                "title": _text(image.get("title")),
                "url": url,
                "media_type": _text(image.get("media_type")),
                "kogl_type": kogl_type,
                "kogl_label": _text(image.get("kogl_label")) or f"공공누리 제{kogl_type[-1]}유형",
                "description": _text(image.get("description")),
                "copyright_display": _text(image.get("copyright_display")),
                "attribution": _text(image.get("attribution")) or "『한국민족문화대백과사전』",
            })
        if not images:
            return None
        return {
            "document_id": document_id,
            "article_title": _text(row.get("article_title")),
            "images": images,
        }

    def get_many(self, document_ids: Iterable[str]) -> list[dict[str, Any]]:
        """입력 문서 순서를 유지하고 같은 문서는 한 번만 반환한다."""
        offsets = self._ensure_index()
        if not offsets:
            return []
        ordered_ids = list(dict.fromkeys(item for item in document_ids if item))
        results = []
        with self.path.open("rb") as stream:
            for document_id in ordered_ids:
                offset = offsets.get(document_id)
                if offset is None:
                    continue
                stream.seek(offset)
                try:
                    row = json.loads(stream.readline())
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                cleaned = self._clean_row(row)
                if cleaned is not None:
                    results.append(cleaned)
        return results


@lru_cache(maxsize=1)
def get_media_catalog() -> MediaCatalog:
    return MediaCatalog(_default_media_path())


def media_for_citations(citations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    document_ids = [
        str(citation.get("document_id") or "")
        for citation in citations
        if isinstance(citation, dict)
    ]
    return get_media_catalog().get_many(document_ids)


def media_catalog_status() -> dict[str, Any]:
    catalog = get_media_catalog()
    return {"available": catalog.available, "path": str(catalog.path)}
