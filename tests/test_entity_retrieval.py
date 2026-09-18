from __future__ import annotations

from copy import deepcopy
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import rag_client
from rag_indexing.entity_matching import matches_name, prioritize_entities
from rag_indexing.hybrid_retriever import HybridRetriever
from rag_service import RagService


def context(doc, title, rank=1, *, kind="인물/전통 인물", aliases=(), section="definition"):
    return {
        "chunk_id": f"{doc}:{section}", "document_id": doc, "title": title,
        "content": f"{title}에 관한 {doc}의 설명.", "source_url": None,
        "section": section, "retrieval_rank": rank, "retrieval_score": 0.5,
        "score_type": "similarity", "metadata": {
            "primary_type": kind, "aliases": list(aliases),
            "document_fingerprint": doc, "chunking_fingerprint": None,
        },
    }


def test_exact_name_survives_dense_only_candidates_and_small_pool():
    # With dense_weight=1.5 every unrelated dense-only result used to beat this
    # lexical hit, even though it is an exact title match.
    dense = [context(f"noise{i}", f"다른 인물{i}", i + 1) for i in range(10)]
    lexical = [context("target", "김유신")]
    before = deepcopy([dense, lexical])
    retriever = HybridRetriever(object(), object(), candidate_k=3)
    result = retriever.fuse_results(dense, lexical, top_k=3, question="김유신 장군")
    assert result[0]["document_id"] == "target"
    assert [r["retrieval_rank"] for r in result] == [1, 2, 3]
    assert [dense, lexical] == before


def test_longer_explicit_title_precedes_overlapping_place_title():
    rows = [context("palace", "경복궁"), context("hall", "경복궁 근정전", 2)]
    assert prioritize_entities("경복궁 근정전", rows)[0]["document_id"] == "hall"


def test_comparison_keeps_both_explicit_entities():
    rows = [context("a", "경복궁"), context("b", "창덕궁", 2)]
    assert {r["document_id"] for r in prioritize_entities("경복궁과 창덕궁 비교", rows)} == {"a", "b"}


def test_role_filters_work_but_does_not_pick_between_two_people():
    rows = [context("book", "이순신", kind="작품/문학"), context("a", "이순신", 2), context("b", "이순신", 3)]
    assert {r["document_id"] for r in prioritize_entities("이순신 장군", rows)} == {"a", "b"}
    assert len(prioritize_entities("이순신", rows)) == 3


def test_unique_catalogue_alias_excludes_other_persons_same_name():
    rows = [context("a", "이순신", aliases=["충무(忠武)"]), context("b", "이순신", 2, aliases=["무의(武毅)"])]
    assert [r["document_id"] for r in prioritize_entities("충무공 이순신", rows)] == ["a"]
    assert [r["document_id"] for r in prioritize_entities("무의공 이순신", rows)] == ["b"]
    # Naming both identities is a comparison, not a choice of one identity.
    assert len(prioritize_entities("충무공 이순신과 무의공 이순신 비교", rows)) == 2


def test_person_and_work_comparison_retains_both_types():
    rows = [context("book", "이순신", kind="작품/문학"), context("person", "이순신", 2)]
    assert len(prioritize_entities("이순신 장군과 소설 이순신 비교", rows)) == 2


def test_name_match_does_not_accept_substrings_or_reorder_phrases():
    assert not matches_name("이순신", "순")
    assert not matches_name("경복궁 사정전", "경복궁 근정전")
    assert matches_name("경복궁 근정전은 언제 지어졌나요", "경복궁 근정전")


@pytest.mark.parametrize("question", ["이순신", "이순신 장군", "이순신 장군에 대해 알려줘", "김유신"])
def test_short_entity_queries_clarify_before_model_can_merge_people(question):
    title = "김유신" if question == "김유신" else "이순신"
    rows = [context("a", title, aliases=["여해(汝諧)"]), context("b", title, 2, aliases=["입부(立夫)"])]
    delegate = Mock()
    request = {"question": question, "retrieved_contexts": rows, "clarification_context": None,
               "audience_level": "easy", "request_id": "req", "interaction_id": "int",
               "schema_version": "0.3.0-draft"}
    result = rag_client.CompoundAwareGenerator(delegate).invoke(request)
    assert result["candidate_response_type"] == "needs_clarification"
    assert len(result["clarification"]["options"]) == 2
    assert "여해" in result["clarification"]["options"][0]["label"]
    delegate.invoke.assert_not_called()


def test_single_document_multiple_chunks_is_not_ambiguous():
    rows = [context("a", "이순신"), context("a", "이순신", 2, section="body")]
    assert rag_client.duplicate_title_clarification({"question": "이순신", "retrieved_contexts": rows}) is None


def test_ui_choice_label_resolves_only_selected_document():
    rows = [context("a", "이순신", aliases=["여해(汝諧)", "충무(忠武)"]),
            context("b", "이순신", 2, aliases=["무의(武毅)", "입부(立夫)"])]
    clarification = rag_client.duplicate_title_clarification({"question": "이순신", "retrieved_contexts": rows})
    selected = clarification["options"][0]["label"]
    assert [r["document_id"] for r in prioritize_entities(f"이순신 ({selected})", rows)] == ["a"]


def test_rule_clarification_satisfies_live_service_summary_contract():
    rows = [context("a", "이순신"), context("b", "이순신", 2)]
    retriever = Mock()
    retriever.search.return_value = rows
    delegate = Mock()
    service = RagService(retriever=retriever, generator=rag_client.CompoundAwareGenerator(delegate),
                         evidence_checker=rag_client.ContentEvidenceChecker())
    result = service.answer_with_trace("이순신 장군", audience_level="easy")["response"]
    assert result["response_type"] == "needs_clarification"
    assert result["summary"] == result["message"] == result["clarification"]["question"]
    delegate.invoke.assert_not_called()


def test_ui_choice_with_commas_is_not_a_compound_question():
    rows = [context("a", "이순신", aliases=["여해(汝諧)", "충무(忠武)"])]
    rows[0]["content"] = "조선시대 정읍현감, 진도군수, 전라좌도수군절도사, 삼도수군통제사 등을 역임한 무신."
    label = rag_client._entity_option_label(rows[0])
    question = f"이순신 장군 ({label})"
    assert rag_client.is_compound(question)  # The legacy list heuristic triggers.
    request = {"question": question, "retrieved_contexts": rows, "clarification_context": None}
    delegate = Mock()
    rag_client.CompoundAwareGenerator(delegate).invoke(request)
    delegate.invoke.assert_called_once_with(request)


def test_arbitrary_parentheses_do_not_bypass_compound_policy():
    request = {"question": "이순신 (경복궁, 창덕궁, 덕수궁을 설명해줘)",
               "retrieved_contexts": [context("a", "이순신")], "clarification_context": None}
    assert not rag_client._is_entity_choice_followup(request)


def role_rows(title="세종"):
    king = context("king", title)
    king["content"] = "조선의 제4대(재위: 1418년~1450년) 왕."
    general = context("general", title, 2)
    general["content"] = "삼국시대 금관국의 후예로서 신라 중고기에 활약한 장군, 관료."
    return [general, king]


@pytest.mark.parametrize("question", ["세종 대왕", "세종대왕", "세종 대왕에 대해 알려줘", "세종 왕"])
def test_explicit_ruler_role_selects_catalogue_king(question):
    assert [r["document_id"] for r in prioritize_entities(question, role_rows())] == ["king"]


def test_role_resolution_is_not_specific_to_sejong():
    assert [r["document_id"] for r in prioritize_entities("태종 대왕", role_rows("태종"))] == ["king"]
    assert [r["document_id"] for r in prioritize_entities("세종 장군", role_rows())] == ["general"]


def test_qualified_person_precedes_generic_role_title():
    vessel = context("vessel", "장군", kind="물품")
    vessel["content"] = "물이나 술을 담는 그릇."
    result = prioritize_entities("세종 장군", [vessel, *role_rows()])
    assert result[0]["document_id"] == "general"


@pytest.mark.parametrize("question", ["세종", "세종 대왕과 세종 장군 비교", "세종은 대왕이 아니야", "세종이 만난 왕"])
def test_role_resolution_does_not_guess_for_unqualified_or_complex_requests(question):
    assert len(prioritize_entities(question, role_rows())) == 2


def test_unknown_occupation_and_two_kings_remain_ambiguous():
    rows = role_rows()
    unknown = context("unknown", "세종", 3)
    unknown["content"] = "조선시대 왕을 보좌한 신하."
    other_king = context("other-king", "세종", 4)
    other_king["content"] = "다른 나라의 왕."
    result = prioritize_entities("세종 대왕", [*rows, unknown, other_king])
    assert {r["document_id"] for r in result} == {"king", "unknown", "other-king"}


def test_body_mention_of_king_is_not_subject_occupation():
    rows = role_rows()
    body = context("general", "세종", 3, section="body")
    body["content"] = "그가 섬긴 인물은 신라의 왕."
    result = prioritize_entities("세종 대왕", [*rows, body])
    assert [r["document_id"] for r in result] == ["king"]
