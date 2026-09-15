"""대표 이미지와 관련 이미지 JSONL을 document_id 기준으로 통합한다.

PyCharm에서 이 파일을 Run 하면 된다. API 호출은 하지 않는다.
"""

from __future__ import annotations

from typing import Any

from media_jsonl_common import PROJECT_ROOT, iter_jsonl, write_jsonl_atomic


RELATED_FILE = PROJECT_ROOT / "data" / "processed" / "aks_related_medias.jsonl"
HEAD_FILE = PROJECT_ROOT / "data" / "processed" / "aks_head_medias.jsonl"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "aks_article_medias.jsonl"


def add_image(record: dict[str, Any], image: Any, *, head: bool) -> None:
    if not isinstance(image, dict):
        return
    mid = str(image.get("mid") or "").strip()
    if not mid:
        return

    images: list[dict[str, Any]] = record["images"]
    existing_index = next(
        (index for index, value in enumerate(images) if value.get("mid") == mid),
        None,
    )
    normalized = dict(image)
    normalized["role"] = "head" if head else "related"

    if existing_index is not None:
        if head:
            existing = images[existing_index]
            for key, value in existing.items():
                if key == "role":
                    continue
                if key not in normalized or is_blank(normalized[key]):
                    normalized[key] = value
            images.pop(existing_index)
            images.insert(0, normalized)
        return
    if head:
        images.insert(0, normalized)
    else:
        images.append(normalized)


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def get_or_create(
    records: dict[str, dict[str, Any]], source: dict[str, Any]
) -> dict[str, Any] | None:
    document_id = str(source.get("document_id") or "").strip()
    if not document_id:
        return None
    record = records.setdefault(
        document_id,
        {
            "document_id": document_id,
            "eid": str(source.get("eid") or "").strip().upper(),
            "article_title": str(source.get("article_title") or "").strip(),
            "images": [],
        },
    )
    if not record["article_title"]:
        record["article_title"] = str(source.get("article_title") or "").strip()
    return record


def main() -> int:
    if not RELATED_FILE.is_file():
        raise SystemExit(
            f"관련 이미지 파일이 없습니다. build_related_medias_jsonl.py를 먼저 실행하세요: "
            f"{RELATED_FILE}"
        )
    if not HEAD_FILE.is_file():
        raise SystemExit(
            f"대표 이미지 파일이 없습니다. build_head_medias_jsonl.py를 먼저 실행하세요: "
            f"{HEAD_FILE}"
        )

    records: dict[str, dict[str, Any]] = {}
    related_count = 0
    head_count = 0
    head_already_related = 0
    head_newly_added = 0

    for _line_number, source in iter_jsonl(RELATED_FILE):
        record = get_or_create(records, source)
        if record is None:
            continue
        for image in source.get("images") or []:
            before = len(record["images"])
            add_image(record, image, head=False)
            related_count += len(record["images"]) - before

    for _line_number, source in iter_jsonl(HEAD_FILE):
        record = get_or_create(records, source)
        if record is None:
            continue
        image = source.get("image")
        before_mids = {value.get("mid") for value in record["images"]}
        add_image(record, image, head=True)
        if isinstance(image, dict) and image.get("mid"):
            head_count += 1
            if image.get("mid") in before_mids:
                head_already_related += 1
            else:
                head_newly_added += 1

    ordered = (records[key] for key in sorted(records))
    written = write_jsonl_atomic(OUTPUT_FILE, ordered)
    print(f"관련 미디어: {related_count:,}건")
    print(f"대표 미디어: {head_count:,}건")
    print(f"관련 미디어와 동일한 대표 미디어: {head_already_related:,}건")
    print(f"통합 배열에 새로 추가된 대표 미디어: {head_newly_added:,}건")
    print(f"완료: {OUTPUT_FILE} ({written:,}줄)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
