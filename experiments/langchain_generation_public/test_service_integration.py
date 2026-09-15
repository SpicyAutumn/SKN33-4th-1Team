"""Real service + LangChain composition; retrieval/model are fixed offline doubles."""
import json
import socket

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from rag_service import RagService, RagServiceConfig, RagServiceError
from test_rag_service import CONTEXT, FakeRetriever, FakeEvidenceChecker
from experiments.langchain_generation_public.generator import LangChainGenerator


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def block(*args, **kwargs): raise AssertionError("Network prohibited")
    monkeypatch.setattr(socket.socket, "connect", block)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")


def build(reply, decision="sufficient"):
    calls = []
    def factory(**kwargs):
        def invoke(prompt, **kw):
            calls.append(prompt)
            if isinstance(reply, Exception): raise reply
            return AIMessage(content=json.dumps(reply, ensure_ascii=False))
        return RunnableLambda(invoke)
    generator = LangChainGenerator(base_url="http://unused.invalid", model="offline", model_factory=factory)
    service = RagService(retriever=FakeRetriever([CONTEXT]), generator=generator,
        evidence_checker=FakeEvidenceChecker([decision]), config=RagServiceConfig(generation_retries=0))
    return service, calls


def response():
    return dict(candidate_response_type="answered", draft_message="ㄱ당은 1928년 대구에서 조직됐습니다.",
        used_chunk_ids=["CTX-1"], clarification=None, premise_correction=None, related_topic_candidates=[])


def test_answer_builds_real_service_citations():
    service, calls = build(response())
    result = service.answer("ㄱ당은 무엇이야?")
    assert result["response_type"] == "answered"
    assert result["citations"][0]["source_url"] == CONTEXT["source_url"]
    assert result["citations"][0]["content"] == CONTEXT["content"]
    assert len(calls) == 1


def test_correction_survives_service_contract():
    data = response()
    data.update(candidate_response_type="corrected_premise", premise_correction={
        "original_premise": "1927년에 조직됐다", "corrected_premise": "1928년입니다.", "source_chunk_ids": ["CTX-1"]})
    service, _ = build(data)
    result = service.answer("ㄱ당은 1927년에 조직된 게 맞아?")
    assert result["response_type"] == "corrected_premise"
    assert result["message"] == data["draft_message"]
    assert result["premise_correction"]["corrected_premise"] == "1928년입니다."
    assert result["citations"]


def test_insufficient_retrieval_skips_model():
    service, calls = build(RuntimeError("must not run"), "insufficient")
    assert service.answer("ㄱ당은 무엇이야?")["response_type"] == "insufficient_evidence"
    assert not calls


def test_unknown_citation_does_not_escape_service():
    data = response()
    data["used_chunk_ids"] = ["nonexistent"]
    service, _ = build(data)
    # The evidence checker still says sufficient: service treats the generator's
    # contradictory refusal as generation_error, rather than a normal abstention.
    with pytest.raises(RagServiceError) as caught:
        service.answer("ㄱ당은 무엇이야?")
    assert caught.value.code == "generation_error"


@pytest.mark.parametrize("failure", [TimeoutError("private endpoint"), ValueError("invalid response")])
def test_upstream_failure_uses_service_error_contract(failure):
    service, calls = build(failure)
    with pytest.raises(RagServiceError) as caught:
        service.answer("ㄱ당은 무엇이야?")
    assert caught.value.code == "upstream_error"
    assert str(caught.value) == "generation call failed"
    assert len(calls) == 1
