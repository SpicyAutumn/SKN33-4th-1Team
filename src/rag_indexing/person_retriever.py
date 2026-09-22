from __future__ import annotations

import json
import re
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

from .bm25_store import _exact_lookup_term, _normalise_metadata, _nullable_text
from .hybrid_retriever import Retriever


# Restrict expansion to introductions; dates, battles, comparisons and monuments
# retain their original retrieval. Whitespace is optional around the honorific.
_INTRODUCTION = re.compile(
    r"^\s*(?P<name>[가-힣]{2,5}?)\s*(?P<honorific>장군|선생|대왕)"
    r"\s*(?:(?:(?:에\s*대해(?:서)?)\s*)?"
    r"(?:알려줘|알려주세요|설명해줘|설명해주세요)"
    r"|(?:은|는)?\s*(?:누구야|누구인가요|어떤\s*사람이야))?\s*[?.!]?\s*$"
)
_MILITARY = re.compile(r"(?:장군|장수|무신|수군통제사|절도사)(?=[\s,.。]|$)")
_MONARCH = re.compile(r"(?:왕|국왕|황제|임금)[.。]?\s*$")


def person_introduction(question: str) -> tuple[str, str] | None:
    match = _INTRODUCTION.fullmatch(question)
    return (match.group("name"), match.group("honorific")) if match else None


def person_option_label(context: dict[str, Any]) -> str:
    # Keep the complete definition so similarly prefixed choices stay distinct.
    return f"{context['title']} — {' '.join(context['content'].split())}"


class PersonDocumentStore:
    """Read existing chunks by exact name and document ID; never rebuild the index."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def _read(self, query: str, parameters: tuple) -> list[dict[str, Any]]:
        with sqlite3.connect(self.database_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
            rows = db.execute(query, parameters).fetchall()
        return [
            {
                "chunk_id": row[0], "document_id": row[1], "title": row[2],
                "content": row[3], "source_url": _nullable_text(row[4]),
                "section": _nullable_text(row[5]), "retrieval_rank": rank,
                "retrieval_score": None, "score_type": "unknown",
                "metadata": _normalise_metadata(json.loads(row[6])),
            }
            for rank, row in enumerate(rows, 1)
        ]

    def definitions(self, name: str) -> list[dict[str, Any]]:
        return self._read(
            """SELECT DISTINCT r.chunk_id,r.document_id,r.title,r.content,
                      r.source_url,r.section,r.metadata_json
               FROM chunk_records r JOIN exact_terms e ON r.chunk_id=e.chunk_id
               WHERE e.term=? AND r.section='definition'
               ORDER BY r.document_id,r.chunk_id""",
            (_exact_lookup_term(name),),
        )

    def document_chunks(self, document_id: str, *, top_k: int) -> list[dict[str, Any]]:
        return self._read(
            """SELECT chunk_id,document_id,title,content,source_url,section,metadata_json
               FROM chunk_records WHERE document_id=? AND section IN ('definition','body')
               ORDER BY CASE section WHEN 'definition' THEN 0 ELSE 1 END,chunk_id
               LIMIT ?""",
            (document_id, top_k),
        )


class PersonTitleRetriever:
    """Resolve honorific introductions using existing definitions, then fetch body.

    No fuzzy name or popularity-based disambiguation. Multiple compatible people
    are marked for the application's deterministic clarification flow. Without a
    local document store, preserve the existing retriever unchanged.
    """

    def __init__(self, retriever: Retriever, document_store: PersonDocumentStore | None = None) -> None:
        self.retriever = retriever
        self.document_store = document_store

    def search(self, question: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        return self._search(question, top_k=top_k)

    def search_with_clarification(
        self, question: str, *, clarification_context: dict[str, Any], top_k: int = 5
    ) -> list[dict[str, Any]]:
        selection = None
        if clarification_context["original_question"].strip() == question.strip():
            selection = clarification_context["clarification_response"].strip()
        return self._search(question, top_k=top_k, selection=selection)

    def _search(
        self, question: str, *, top_k: int, selection: str | None = None
    ) -> list[dict[str, Any]]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        original = self.retriever.search(question, top_k=top_k)
        introduction = person_introduction(question)
        # The web UI currently submits "original question (option label)".
        # Accept only labels checked against this question's actual candidates.
        if introduction is None and selection is None:
            followup = re.fullmatch(r"(.+?) \((.+)\)", question.strip())
            if followup:
                introduction = person_introduction(followup.group(1))
                selection = followup.group(2)
        if introduction is None or self.document_store is None:
            return original
        name, honorific = introduction
        by_document = {}
        for context in self.document_store.definitions(name):
            kind = context["metadata"].get("primary_type") or context["metadata"].get("contents_type") or ""
            if kind.startswith("인물/"):
                by_document.setdefault(context["document_id"], context)
        candidates = list(by_document.values())
        if honorific == "대왕":
            candidates = [c for c in candidates if _MONARCH.search(c["content"])]
        elif honorific == "장군":
            candidates = [c for c in candidates if _MILITARY.search(c["content"])]
        if not candidates:
            return original
        selection_resolved = False
        if selection:
            selected = [c for c in candidates if person_option_label(c) == selection]
            if len(selected) == 1:
                candidates = selected
                selection_resolved = True
        ambiguous = len(candidates) > 1
        if ambiguous:
            contexts = deepcopy(candidates[:top_k])
            for context in contexts:
                context["metadata"]["person_ambiguous"] = True
                context["metadata"]["person_candidate_count"] = len(candidates)
        else:
            contexts = self.document_store.document_chunks(candidates[0]["document_id"], top_k=top_k)
            if not contexts:
                contexts = deepcopy(candidates)
        originals = {c["chunk_id"]: c for c in original}
        for rank, context in enumerate(contexts, 1):
            context["retrieval_rank"] = rank
            if selection_resolved:
                context["metadata"]["person_selection_resolved"] = True
            if context["chunk_id"] in originals:
                previous = originals[context["chunk_id"]]
                context["retrieval_score"] = previous["retrieval_score"]
                context["score_type"] = previous["score_type"]
        return contexts


def person_clarification(contexts: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [c for c in contexts if c.get("metadata", {}).get("person_ambiguous") is True]
    if not candidates:
        return None
    return {
        "reason_code": "ambiguous_entity",
        "question": "같은 이름과 호칭에 해당하는 인물이 여러 명입니다. 어느 인물을 말씀하시나요?",
        "options": [
            {"id": f"person-{index}", "label": person_option_label(c), "source_chunk_ids": [c["chunk_id"]]}
            for index, c in enumerate(candidates[:3], 1)
        ],
    }
