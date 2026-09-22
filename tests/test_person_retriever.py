from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

from rag_indexing.bm25_store import build_bm25_index
from rag_indexing.person_retriever import (
    PersonDocumentStore, PersonTitleRetriever, person_clarification, person_option_label,
)
from rag_service.service import RagService

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import rag_client
import retrieval


def chunk(doc, title, content, section="definition", kind="인물/전통 인물", aliases=None):
    return {
        "chunk_id": f"{doc}:{section}", "document_id": doc, "title": title,
        "content": content, "section": section, "source_url": None,
        "retrieval_rank": 1, "retrieval_score": 0.5, "score_type": "similarity",
        "metadata": {"aliases": aliases or [], "primary_type": kind,
                     "document_fingerprint": doc, "chunking_fingerprint": None},
    }


class BaseRetriever:
    def __init__(self, results=None):
        self.results = results or [chunk("wrong", "순장", "다른 자료")]
        self.calls = []

    def search(self, question, *, top_k=5):
        self.calls.append(question)
        return deepcopy(self.results[:top_k])


@pytest.fixture
def store(tmp_path):
    records = [
        chunk("king", "세종", "조선의 제4대 왕."),
        chunk("general", "세종", "신라에서 활약한 장군, 관료."),
        chunk("gang", "강감찬", "고려의 상원수대장군, 문하시중."),
        chunk("admiral", "이순신", "정읍현감, 진도군수, 삼도수군통제사 등을 역임한 무신."),
        chunk("homonym", "이순신", "선무공신 3등에 책록된 무신."),
        chunk("novel", "이순신", "이순신 장군의 전기 소설.", kind="작품/문학"),
        chunk("scholar", "이이", "성학집요를 저술한 문신."),
        chunk("official", "이이", "장령을 역임한 문신."),
        chunk("poet", "시인", "시를 지은 학자.", aliases=["별칭"]),
    ]
    records += [chunk(r["document_id"], r["title"], f"{r['document_id']}의 생애와 활동 본문", "body")
                for r in records]
    path = tmp_path / "index.sqlite3"
    build_bm25_index(records, path)
    return PersonDocumentStore(path)


@pytest.mark.parametrize("question", ["세종 대왕", "세종대왕", "세종 대왕에 대해 알려줘"])
def test_king_excludes_homonymous_general_and_fetches_body(store, question):
    result = PersonTitleRetriever(BaseRetriever(), store).search(question, top_k=3)
    assert {c["document_id"] for c in result} == {"king"}
    assert [c["section"] for c in result] == ["definition", "body"]
    assert all(c["retrieval_score"] is None and c["score_type"] == "unknown" for c in result)


@pytest.mark.parametrize("question", ["강감찬 장군", "강감찬 장군 알려줘", "강감찬장군에 대해 알려줘"])
def test_military_role_can_be_in_a_longer_official_title(store, question):
    result = PersonTitleRetriever(BaseRetriever(), store).search(question)
    assert {c["document_id"] for c in result} == {"gang"}
    assert any(c["section"] == "body" for c in result)


def test_homonyms_are_offered_without_mixing_bodies_or_novels(store):
    result = PersonTitleRetriever(BaseRetriever(), store).search("이순신 장군", top_k=3)
    assert {c["document_id"] for c in result} == {"admiral", "homonym"}
    assert all(c["section"] == "definition" for c in result)
    assert len(person_clarification(result)["options"]) == 2


def test_short_name_exact_lookup_recovers_both_people(store):
    result = PersonTitleRetriever(BaseRetriever(), store).search("이이 선생")
    assert {c["document_id"] for c in result} == {"scholar", "official"}
    assert person_clarification(result) is not None


def test_top_one_does_not_hide_known_ambiguity(store):
    result = PersonTitleRetriever(BaseRetriever(), store).search("이순신 장군", top_k=1)
    assert len(result) == 1
    assert result[0]["metadata"]["person_candidate_count"] == 2
    assert person_clarification(result) is not None


@pytest.mark.parametrize("question", ["경복궁에 대해 알려줘", "훈민정음은 누가 만들었어?",
    "임진왜란은 언제 일어났어?", "이순신", "장군의 역할", "이순몽 장군 묘",
    "이순신 장군의 사망 연도", "이순신 장군과 강감찬 장군 비교"])
def test_unrelated_queries_are_unchanged(store, question):
    base = BaseRetriever()
    before = deepcopy(base.results)
    assert PersonTitleRetriever(base, store).search(question) == before
    assert base.calls == [question]
    assert base.results == before


def test_without_store_or_matching_person_preserves_original(store):
    base = BaseRetriever()
    assert PersonTitleRetriever(base).search("세종대왕") == base.results
    assert PersonTitleRetriever(base, store).search("없는이 장군") == base.results


def test_alias_lookup_and_readonly_store(store):
    before = store.database_path.read_bytes()
    results = PersonTitleRetriever(BaseRetriever(), store).search("별칭 선생")
    assert {c["document_id"] for c in results} == {"poet"}
    assert store.database_path.read_bytes() == before


def test_original_score_retained_only_for_original_chunk(store):
    base = BaseRetriever([chunk("king", "세종", "조선의 제4대 왕.")])
    result = PersonTitleRetriever(base, store).search("세종대왕")
    assert result[0]["retrieval_score"] == 0.5
    assert result[1]["retrieval_score"] is None
    assert [c["retrieval_rank"] for c in result] == [1, 2]


def followup(label):
    return {"original_question": "이순신 장군", "clarification_question": "어느 인물인가요?",
            "clarification_response": label, "clarification_turn_count": 1}


class AnswerGenerator:
    def invoke(self, request):
        return {
            "schema_version": request["schema_version"], "request_id": request["request_id"],
            "interaction_id": request["interaction_id"], "candidate_response_type": "answered",
            "summary": "생애를 설명합니다.", "draft_message": "생애를 설명합니다.",
            "audience_level": request["audience_level"],
            "used_chunk_ids": [c["chunk_id"] for c in request["retrieved_contexts"]],
            "clarification": None, "premise_correction": None, "related_topic_candidates": [],
            "generation_metadata": {},
        }


def test_full_clarification_then_choice_fetches_only_selected_body(store, monkeypatch):
    delegate = Mock(wraps=AnswerGenerator())
    service = RagService(retriever=PersonTitleRetriever(BaseRetriever(), store),
                         generator=rag_client.CompoundAwareGenerator(delegate),
                         evidence_checker=rag_client.ContentEvidenceChecker())
    monkeypatch.setattr(retrieval, "get_service", lambda: service)
    first = retrieval.answer("이순신 장군")
    assert first["response"]["response_type"] == "needs_clarification"
    delegate.invoke.assert_not_called()
    options = first["response"]["clarification"]["options"]
    chosen = next(o for o in options if "삼도수군통제사" in o["label"])
    # The UI passes its cached ambiguous contexts; they must be discarded.
    second = retrieval.answer("이순신 장군", clarification_context=followup(chosen["label"]),
                              retrieved_contexts=first["retrieved_contexts"])
    assert second["response"]["response_type"] == "answered"
    assert {c["document_id"] for c in second["retrieved_contexts"]} == {"admiral"}
    assert any(c["section"] == "body" for c in second["retrieved_contexts"])
    delegate.invoke.assert_called_once()


def test_web_ui_label_followup_resolves_the_same_document(store):
    retriever = PersonTitleRetriever(BaseRetriever(), store)
    candidates = retriever.search("이순신 장군")
    chosen = next(c for c in candidates if c["document_id"] == "admiral")
    result = retriever.search(f"이순신 장군 ({person_option_label(chosen)})")
    assert {c["document_id"] for c in result} == {"admiral"}
    assert any(c["section"] == "body" for c in result)
    service = RagService(retriever=retriever,
                         generator=rag_client.CompoundAwareGenerator(AnswerGenerator()),
                         evidence_checker=rag_client.ContentEvidenceChecker())
    # Commas in the selected definition must not trigger compound-question gating.
    response = service.answer(f"이순신 장군 ({person_option_label(chosen)})")
    assert response["response_type"] == "answered"


def test_invalid_selection_does_not_guess_or_send_mixed_people_to_model(store):
    delegate = Mock()
    service = RagService(retriever=PersonTitleRetriever(BaseRetriever(), store),
                         generator=rag_client.CompoundAwareGenerator(delegate),
                         evidence_checker=rag_client.ContentEvidenceChecker())
    result = service.answer("이순신 장군", clarification_context=followup("알아서 골라줘"))
    assert result["response_type"] == "insufficient_evidence"
    delegate.invoke.assert_not_called()


@pytest.mark.parametrize("mode", ["hybrid", "dense"])
@pytest.mark.parametrize("document_id", ["admiral", "homonym"])
def test_selected_source_lookup_through_service_factory(store, monkeypatch, mode, document_id):
    """A UI selection must reach generation through the deployed retriever wrappers."""
    chosen = next(c for c in store.definitions("이순신") if c["document_id"] == document_id)
    dense = Mock()
    dense.search.return_value = [deepcopy(chosen)]
    dense.fetch_by_ids.return_value = [deepcopy(chosen)]
    monkeypatch.setattr("rag_indexing.pinecone_store.PineconeRetriever", lambda: dense)
    path = store.database_path if mode == "hybrid" else store.database_path.with_name("absent.sqlite3")
    monkeypatch.setattr(rag_client, "bm25_index_path", lambda: path)
    monkeypatch.setattr(rag_client, "missing_env", lambda: [])
    generator = Mock(wraps=AnswerGenerator())
    monkeypatch.setattr("rag_service.ollama_generator.OllamaGenerator", lambda: generator)
    service = rag_client.build_service()
    monkeypatch.setattr(retrieval, "get_service", lambda: service)
    label = person_option_label(chosen)

    result = retrieval.answer(
        label + "에 대해 자세히 알려주세요.",
        interaction_id="INT-selected-source", clarification_context=followup(label),
        selected_source_chunk_ids=[chosen["chunk_id"]],
    )

    dense.fetch_by_ids.assert_called_once_with([chosen["chunk_id"]])
    generator.invoke.assert_called_once()
    assert result["response"]["response_type"] == "answered"
    assert result["retrieved_contexts"][0]["chunk_id"] == chosen["chunk_id"]
