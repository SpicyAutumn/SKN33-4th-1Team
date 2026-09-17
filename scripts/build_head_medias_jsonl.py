"""항목 목록 API 원본의 headMedia에서 공공누리 대표 미디어 JSONL을 만든다.

PyCharm에서 이 파일을 Run 하면 된다. 기존에 수집된 목록 API 원본을 읽으므로
추가 API 호출은 하지 않는다.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from media_jsonl_common import (
    PROJECT_ROOT,
    find_article_list_metadata_dir,
    is_displayable_media,
    normalized_image,
    write_jsonl_atomic,
)


OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "aks_head_medias.jsonl"


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON 파일을 읽을 수 없습니다: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 객체 형식이 아닙니다: {path}")
    return value


def build_records(metadata_dir: Path) -> Iterator[dict[str, Any]]:
    files = sorted(metadata_dir.glob("E*.json"))
    if not files:
        raise FileNotFoundError(f"EID별 목록 API JSON이 없습니다: {metadata_dir}")

    included = 0
    excluded = 0
    for index, path in enumerate(files, start=1):
        article = read_json_object(path)
        eid = str(article.get("eid") or path.stem).strip().upper()
        head_media = article.get("headMedia")

        if not is_displayable_media(head_media):
            excluded += 1
        else:
            included += 1
            yield {
                "document_id": f"aks:{eid}",
                "eid": eid,
                "article_title": str(article.get("headword") or "").strip(),
                "image": normalized_image(head_media, role="head"),
            }

        if index % 5000 == 0 or index == len(files):
            print(
                f"진행: {index:,}/{len(files):,} / "
                f"대표 미디어 {included:,}건 / 제외 {excluded:,}건",
                flush=True,
            )


def main() -> int:
    metadata_dir = find_article_list_metadata_dir()
    print(f"입력: {metadata_dir}")
    written = write_jsonl_atomic(OUTPUT_FILE, build_records(metadata_dir))
    print(f"완료: {OUTPUT_FILE} ({written:,}줄)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
