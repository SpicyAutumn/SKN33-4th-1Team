"""Keep explicit catalogue entities when semantic and lexical rankings disagree.

This uses catalogue titles, aliases and types, never a list of preferred people.
It does not infer an identity from popularity or invent missing evidence.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .bm25_store import tokenize_korean

_WORDS = re.compile(r"[0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ]+")
PERSON_ROLES = ("장군", "선생", "시인", "작가", "화가", "왕", "대왕")


def _words(text: str) -> list[str]:
    return _WORDS.findall(unicodedata.normalize("NFC", text).lower())


def matches_name(question: str, name: str, *, alias: bool = False) -> bool:
    """Match consecutive complete words, permitting the existing particle rules."""
    target = _words(name)
    words = _words(question)
    if not target or not words:
        return False
    variants = [set(tokenize_korean(word)) for word in words]
    if alias:
        # A posthumous name in the catalogue is often used with the honorific 公.
        for word, choices in zip(words, variants):
            if word.endswith("공") and len(word) > 2:
                choices.add(word[:-1])
    return any(
        all(term in choices for term, choices in zip(target, variants[start:]))
        for start in range(len(words) - len(target) + 1)
    )


def distinct_aliases(context: dict[str, Any]) -> list[str]:
    title = _words(str(context.get("title") or ""))
    return [
        alias for alias in context.get("metadata", {}).get("aliases", [])
        if _words(alias) and _words(alias) != title
    ]


def prioritize_entities(
    question: str, results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Promote exact names before truncation; separate uniquely qualified names.

    Remaining candidates keep their RRF order. Multiple explicitly named entities
    remain available, so comparison questions do not become single-document QA.
    """
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for item in results:
        title = str(item.get("title") or "")
        if matches_name(question, title):
            groups.setdefault(title, {}).setdefault(item["document_id"], []).append(item)

    excluded: set[str] = set()
    # A comparison may explicitly request both a person and a work of that name.
    work_request = any(matches_name(question, kind) for kind in ("소설", "작품", "책", "영화", "전기"))
    person_request = not work_request and any(matches_name(question, role) for role in PERSON_ROLES)
    for documents in groups.values():
        if len(documents) < 2:
            continue
        alias_matches = {
            doc for doc, chunks in documents.items()
            if any(matches_name(question, a, alias=True) for c in chunks for a in distinct_aliases(c))
        }
        if len(alias_matches) == 1:
            excluded.update(set(documents) - alias_matches)
        elif person_request:
            people = {
                doc for doc, chunks in documents.items()
                if any(str(c.get("metadata", {}).get("primary_type") or "").startswith("인물") for c in chunks)
            }
            if people:
                # Unknown types cannot safely be ruled out.
                excluded.update(
                    doc for doc, chunks in documents.items() if doc not in people
                    and all(c.get("metadata", {}).get("primary_type") for c in chunks)
                )

    def order(pair: tuple[int, dict[str, Any]]) -> tuple[int, int, int, int]:
        rank, item = pair
        title = str(item.get("title") or "")
        title_length = len("".join(_words(title))) if matches_name(question, title) else 0
        alias_length = max(
            (len("".join(_words(a))) for a in distinct_aliases(item) if matches_name(question, a, alias=True)),
            default=0,
        )
        matched = max(title_length, alias_length)
        return (-bool(alias_length), -matched, 0 if matched and item.get("section") == "definition" else 1, rank)

    return [item for _, item in sorted(
        ((rank, item) for rank, item in enumerate(results) if item["document_id"] not in excluded),
        key=order,
    )]
