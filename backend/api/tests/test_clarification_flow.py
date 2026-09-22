import json
import os
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")

import django

django.setup()

from django.test import RequestFactory, SimpleTestCase

from api import rag_runtime, views


class ClarificationRuntimeTest(SimpleTestCase):
    def test_runtime_forwards_followup_context_to_rag_service(self):
        context = {
            "original_question": "이순신 장군",
            "clarification_question": "어느 인물을 말씀하시나요?",
            "clarification_response": "선무공신 이순신",
            "clarification_turn_count": 1,
        }
        retrieval = type("Retrieval", (), {})()
        retrieval.answer = lambda *args, **kwargs: {
            "response": {"response_type": "answered", "citations": []}
        }
        client = type("Client", (), {"missing_env": staticmethod(lambda: [])})()

        with patch.object(rag_runtime, "_retrieval_module", return_value=(client, retrieval)):
            with patch.object(retrieval, "answer", wraps=retrieval.answer) as answer:
                rag_runtime.answer(
                    "선무공신 이순신에 대해 알려주세요.",
                    audience_level="general",
                    interaction_id="INT-1",
                    clarification_context=context,
                    selected_source_chunk_ids=["aks:E0044901:definition:0001"],
                )

        answer.assert_called_once_with(
            "선무공신 이순신에 대해 알려주세요.",
            audience_level="general",
            interaction_id="INT-1",
            clarification_context=context,
            selected_source_chunk_ids=["aks:E0044901:definition:0001"],
        )


class ClarificationApiTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_search_endpoint_forwards_followup_fields(self):
        context = {
            "original_question": "이순신 장군",
            "clarification_question": "어느 인물을 말씀하시나요?",
            "clarification_response": "선무공신 이순신",
            "clarification_turn_count": 1,
        }
        request = self.factory.post(
            "/api/v1/searches",
            data=json.dumps({
                "question": "선무공신 이순신에 대해 알려주세요.",
                "audience_level": "general",
                "interaction_id": "INT-1",
                "clarification_context": context,
                "selected_source_chunk_ids": ["aks:E0044901:definition:0001"],
            }),
            content_type="application/json",
        )
        response_payload = {
            "request_id": "REQ-2",
            "interaction_id": "INT-1",
            "response_type": "answered",
            "message": "답변",
            "citations": [],
        }

        with patch.object(views, "rag_answer", return_value=response_payload) as answer:
            response = views.searches(request)

        self.assertEqual(response.status_code, 200)
        answer.assert_called_once_with(
            "선무공신 이순신에 대해 알려주세요.",
            audience_level="general",
            interaction_id="INT-1",
            clarification_context=context,
            selected_source_chunk_ids=["aks:E0044901:definition:0001"],
        )

    def test_search_endpoint_rejects_non_object_followup_context(self):
        request = self.factory.post(
            "/api/v1/searches",
            data=json.dumps({
                "question": "질문",
                "audience_level": "general",
                "clarification_context": "invalid",
            }),
            content_type="application/json",
        )

        response = views.searches(request)

        self.assertEqual(response.status_code, 422)

    def test_search_endpoint_rejects_too_many_selected_sources(self):
        request = self.factory.post(
            "/api/v1/searches",
            data=json.dumps({
                "question": "질문",
                "audience_level": "general",
                "selected_source_chunk_ids": ["c1", "c2", "c3", "c4"],
            }),
            content_type="application/json",
        )

        response = views.searches(request)

        self.assertEqual(response.status_code, 422)

    def test_search_endpoint_rejects_selected_source_without_clarification_context(self):
        request = self.factory.post(
            "/api/v1/searches",
            data=json.dumps({
                "question": "질문",
                "audience_level": "general",
                "selected_source_chunk_ids": ["c1"],
            }),
            content_type="application/json",
        )

        response = views.searches(request)

        self.assertEqual(response.status_code, 422)
