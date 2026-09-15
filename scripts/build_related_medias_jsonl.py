"""기존 원문 JSONL의 relatedMedias에서 표시 가능한 미디어 JSONL을 만든다.

PyCharm에서 이 파일을 Run 하면 된다. 추가 API 호출은 하지 않는다.
"""

from __future__ import annotations

from collections.abc import Iterator

from media_jsonl_common import (
    PROJECT_ROOT,
    find_articles_jsonl,
    is_displayable_media,
    iter_jsonl,
    normalized_image,
    write_jsonl_atomic,
)


OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "aks_related_medias.jsonl"


def build_records(input_file) -> Iterator[dict]:
    scanned = 0
    included_articles = 0
    included_images = 0

    for _line_number, article in iter_jsonl(input_file):
        scanned += 1
        eid = str(article.get("eid") or "").strip().upper()
        if not eid:
            continue

        images = []
        seen_mids = set()
        for media in article.get("relatedMedias") or []:
            if not is_displayable_media(media):
                continue
            mid = str(media.get("mid") or "").strip()
            if not mid or mid in seen_mids:
                continue
            seen_mids.add(mid)
            images.append(normalized_image(media, role="related"))

        if images:
            included_articles += 1
            included_images += len(images)
            yield {
                "document_id": f"aks:{eid}",
                "eid": eid,
                "article_title": str(article.get("headword") or "").strip(),
                "images": images,
            }

        if scanned % 5000 == 0:
            print(
                f"진행: 항목 {scanned:,}건 확인 / "
                f"미디어 있는 항목 {included_articles:,}건 / 미디어 {included_images:,}건",
                flush=True,
            )

    print(
        f"필터 완료: 항목 {scanned:,}건 / "
        f"미디어 있는 항목 {included_articles:,}건 / 미디어 {included_images:,}건"
    )


def main() -> int:
    input_file = find_articles_jsonl()
    print(f"입력: {input_file}")
    written = write_jsonl_atomic(OUTPUT_FILE, build_records(input_file))
    print(f"완료: {OUTPUT_FILE} ({written:,}줄)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
