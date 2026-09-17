import copy
import json
import socket

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from experiments.langchain_generation_public.generator import LangChainGenerator
from rag_service.ollama_generator import OllamaGenerator
from test_ollama_generator import generation_request


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network is prohibited in offline tests")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")


def output(kind="answered", ids=None):
    return dict(candidate_response_type=kind, draft_message="경복궁에 대한 설명입니다.",
                used_chunk_ids=["CTX-1"] if ids is None else ids,
                clarification=None, premise_correction=None, related_topic_candidates=[])


@pytest.mark.parametrize("level", ["easy", "general", "advanced"])
@pytest.mark.parametrize("with_summary", [False, True])
@pytest.mark.parametrize("case", ["answer", "unknown_source", "insufficient", "correction", "clarification"])
def test_parity(level, case, with_summary):
    request = generation_request()
    request["audience_level"] = level
    data = output()
    if with_summary:
        data["summary"] = "모델이 반환한 핵심 요약입니다."
    if case == "unknown_source":
        data["used_chunk_ids"] = ["missing"]
    elif case == "insufficient":
        data["candidate_response_type"] = "insufficient_evidence"
    elif case == "correction":
        data["premise_correction"] = dict(original_premise="잘못된 전제",
            corrected_premise="교정 내용", source_chunk_ids=["CTX-1"])
    elif case == "clarification":
        data["candidate_response_type"] = "needs_clarification"
        data["clarification"] = {"options": [{"source_chunk_ids": ["CTX-1"]}]}
    raw = json.dumps(data, ensure_ascii=False)
    capture = {}
    def transport(url, payload, timeout):
        capture["payload"] = payload
        return dict(message={"content": raw}, model="test-model", done_reason="stop",
                    prompt_eval_count=20, eval_count=10)
    def factory(**kwargs):
        capture["options"] = kwargs
        def reply(prompt, **kwargs):
            assert kwargs == {"stream": False}
            capture["messages"] = prompt.to_messages()
            return AIMessage(content=raw, response_metadata={"model": "test-model", "done_reason": "stop"},
                usage_metadata={"input_tokens": 20, "output_tokens": 10, "total_tokens": 30})
        return RunnableLambda(reply)
    original_request = copy.deepcopy(request)
    expected = OllamaGenerator(base_url="http://unused.invalid", model="test-model", transport=transport).invoke(request)
    actual = LangChainGenerator(base_url="http://unused.invalid", model="test-model", model_factory=factory).invoke(request)
    expected["generation_metadata"].pop("latency_ms")
    actual["generation_metadata"].pop("latency_ms")
    assert actual == expected
    assert actual["summary"] == data.get("summary", data["draft_message"])
    assert request == original_request
    assert [m.content for m in capture["messages"]] == [m["content"] for m in capture["payload"]["messages"]]
    opts = capture["options"]
    assert opts["num_predict"] == capture["payload"]["options"]["num_predict"]
    assert opts["format"] == capture["payload"]["format"]
    assert "summary" in opts["format"]["required"]
    assert opts["format"]["properties"]["summary"]["type"] == "string"
    assert opts["reasoning"] is False
    assert opts["client_kwargs"] == {"timeout": 120.0}


@pytest.mark.parametrize("raw", ["not json", "[]", "{}"])
def test_malformed_response_rejected(raw):
    factory = lambda **kwargs: RunnableLambda(lambda p, **kw: AIMessage(content=raw))
    with pytest.raises(ValueError):
        LangChainGenerator(base_url="http://unused.invalid", model="test", model_factory=factory).invoke(generation_request())


def test_model_failure_propagates():
    def fail(prompt, **kwargs):
        raise TimeoutError("simulated timeout")
    factory = lambda **kwargs: RunnableLambda(fail)
    with pytest.raises(TimeoutError):
        LangChainGenerator(base_url="http://unused.invalid", model="test", model_factory=factory).invoke(generation_request())


def test_real_sdk_request_without_network():
    from unittest.mock import patch
    captured = {}
    def chat(client, **kwargs):
        captured.update(kwargs)
        return dict(message={"role": "assistant", "content": json.dumps(output())},
                    model="test", done=True, done_reason="stop", prompt_eval_count=20, eval_count=10)
    with patch("ollama.Client.chat", chat):
        result = LangChainGenerator(base_url="http://unused.invalid", model="test").invoke(generation_request())
    assert captured["stream"] is False
    assert captured["think"] is False
    assert captured["options"]["num_predict"] == 640
    assert isinstance(captured["format"], dict)
    assert result["generation_metadata"]["token_usage"]["total_tokens"] == 30
