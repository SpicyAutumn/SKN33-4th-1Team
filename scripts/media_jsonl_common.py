"""두 미디어 JSONL 생성 스크립트가 공유하는 작은 유틸리티."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ARTICLES_JSONL = PROJECT_ROOT / "data" / "raw" / "aks_full_content.jsonl"
LEGACY_ARTICLES_JSONL = Path(
    r"C:\SKN_AI\SKN33-3rd-1Team\data\raw\aks_full_content.jsonl"
)
LOCAL_LIST_METADATA_DIR = PROJECT_ROOT / "data" / "raw" / "api_list_metadata"
LEGACY_LIST_METADATA_DIR = Path(
    r"C:\SKN_AI\SKN33-3rd-1Team\data\raw\api_list_metadata"
)
ALLOWED_KOGL_TYPES = {"KOGL1", "KOGL2", "KOGL3", "KOGL4"}
ALLOWED_MEDIA_TYPES = {"사진", "지도", "차트"}
KOGL_LABELS = {
    "KOGL1": "공공누리 제1유형",
    "KOGL2": "공공누리 제2유형",
    "KOGL3": "공공누리 제3유형",
    "KOGL4": "공공누리 제4유형",
}
ZERO_MID = "00000000-0000-0000-0000-000000000000"


def find_articles_jsonl() -> Path:
    configured = os.getenv("AKS_ARTICLES_JSONL", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.extend([LOCAL_ARTICLES_JSONL, LEGACY_ARTICLES_JSONL])
    for path in candidates:
        if path.is_file():
            return path.resolve()
    checked = "\n".join(f"- {path}" for path in candidates)
    raise FileNotFoundError(
        "aks_full_content.jsonl을 찾지 못했습니다. 확인한 위치:\n" + checked
    )


def find_article_list_metadata_dir() -> Path:
    configured = os.getenv("AKS_ARTICLE_LIST_METADATA_DIR", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.extend([LOCAL_LIST_METADATA_DIR, LEGACY_LIST_METADATA_DIR])
    for path in candidates:
        if path.is_dir():
            return path.resolve()
    checked = "\n".join(f"- {path}" for path in candidates)
    raise FileNotFoundError(
        "api_list_metadata 폴더를 찾지 못했습니다. 확인한 위치:\n" + checked
    )


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} JSON 형식 오류") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} 객체 형식이 아닙니다.")
            yield line_number, value


def valid_head_mid(value: Any) -> str | None:
    mid = str(value or "").strip()
    return mid if mid and mid != ZERO_MID else None


def is_displayable_media(media: Any) -> bool:
    if not isinstance(media, dict):
        return False
    return (
        str(media.get("mediaType") or "").strip() in ALLOWED_MEDIA_TYPES
        and str(media.get("koglType") or "").strip().upper() in ALLOWED_KOGL_TYPES
        and bool(str(media.get("url") or "").strip())
    )


def normalized_image(media: dict[str, Any], *, role: str) -> dict[str, Any]:
    kogl_type = str(media.get("koglType") or "").strip().upper()
    caption = str(media.get("caption") or "").strip()
    return {
        "mid": str(media.get("mid") or "").strip(),
        "role": role,
        "title": caption,
        "url": str(media.get("url") or "").strip(),
        "media_type": str(media.get("mediaType") or "").strip(),
        "kogl_type": kogl_type,
        "kogl_label": KOGL_LABELS.get(kogl_type, kogl_type),
        "description": str(media.get("description") or "").strip(),
        "copyright_display": str(media.get("copyrightDisplay") or "").strip(),
        "attribution": (
            f"{caption}, 『한국민족문화대백과사전』"
            if caption
            else "『한국민족문화대백과사전』"
        ),
    }


def write_jsonl_atomic(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")
            count += 1
    temporary.replace(path)
    return count
