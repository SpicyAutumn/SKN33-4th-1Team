"""Experimental LangChain prompt/model path; production wiring is unchanged."""
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama

from rag_service.ollama_generator import OllamaGenerator


class LangChainGenerator(OllamaGenerator):
    """Replace the model transport while inheriting existing contract repairs.

    Explicit endpoint/model avoid loading a teammate's environment settings.
    The injected factory supports offline model simulation in tests.
    """

    def __init__(self, *, base_url: str, model: str, model_factory=None, **kwargs):
        if "transport" in kwargs:
            raise ValueError("Use model_factory for offline tests")
        self.model_factory = model_factory or ChatOllama
        super().__init__(base_url=base_url, model=model,
                         transport=self._langchain_transport, **kwargs)

    def _langchain_transport(self, url: str, payload: dict, timeout: float) -> dict:
        # Template variables keep literal JSON braces in the original messages intact.
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_text}"), ("human", "{request_text}")
        ])
        model = self.model_factory(
            base_url=self.base_url,
            model=payload["model"],
            temperature=payload["options"]["temperature"],
            num_predict=payload["options"]["num_predict"],
            reasoning=False,
            format=payload["format"],
            keep_alive=payload["keep_alive"],
            client_kwargs={"timeout": timeout},
            disable_streaming=True,
        )
        chain = prompt | model.bind(stream=False) | RunnableLambda(self._to_ollama_response)
        return chain.invoke({
            "system_text": payload["messages"][0]["content"],
            "request_text": payload["messages"][1]["content"],
        })

    @staticmethod
    def _to_ollama_response(message: Any) -> dict:
        if not isinstance(message.content, str):
            raise ValueError("Expected textual structured model output")
        meta = message.response_metadata or {}
        usage = message.usage_metadata or {}
        # Preserve native counts where available; otherwise use normalized counts.
        return {
            "message": {"content": message.content},
            "model": meta.get("model") or meta.get("model_name"),
            "done_reason": meta.get("done_reason"),
            "prompt_eval_count": meta.get("prompt_eval_count", usage.get("input_tokens")),
            "eval_count": meta.get("eval_count", usage.get("output_tokens")),
        }
