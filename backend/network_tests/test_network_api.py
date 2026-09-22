"""No production settings, credentials, DB, or external services are loaded."""
import json
import unittest
from unittest.mock import patch

from django.conf import settings
if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", SECRET_KEY="offline-network-test")
from django.test import RequestFactory
from api import network_runtime, network_views


class NetworkApiTest(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        network_runtime.build_network.cache_clear()
        network_runtime.build_network_for_question.cache_clear()
        network_runtime._recommendations.cache_clear()

    def get(self, **query):
        return network_views.heritage_network(self.factory.get("/api/v1/heritage-network", query))

    def test_invalid_inputs_do_not_reach_runtime(self):
        cases = [{}, {"document_id": "../../etc"}, {"question": "가" * 501},
                 {"question": "청자", "document_id": "aks:E1"},
                 {"document_ids": ",".join(["aks:E1"] * 11)},
                 {"question": "청자", "document_ids": "bad"}]
        with patch.object(network_views, "build_network") as by_id, patch.object(network_views, "build_network_for_question") as by_question:
            for query in cases:
                with self.subTest(query=query):
                    self.assertEqual(self.get(**query).status_code, 422)
            by_id.assert_not_called()
            by_question.assert_not_called()

    def test_post_is_disallowed(self):
        self.assertEqual(network_views.heritage_network(self.factory.post("/", {})).status_code, 405)

    def test_unavailable_is_sanitized(self):
        with patch.object(network_views, "build_network", side_effect=network_runtime.HeritageNetworkUnavailableError("internal detail")):
            response = self.get(document_id="aks:E1")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"internal detail", response.content)

    def test_real_catalog_question_and_choices_without_services(self):
        graph = network_runtime._graph_module()
        with patch.object(graph, "build_neighbors", side_effect=AssertionError("external call")):
            response = self.get(question="경복궁에 대해 알려줘")
            self.assertEqual(response.status_code, 200)
            body = json.loads(response.content)
            self.assertEqual(body["root"]["title"], "경복궁")
            self.assertEqual(body["mode"], "catalog")
            choice = json.loads(self.get(question="경복궁과 창덕궁의 차이").content)
            self.assertTrue(choice["requires_selection"])
            self.assertEqual({entry["title"] for entry in choice["candidates"]}, {"경복궁", "창덕궁"})
            selected = self.get(document_id=choice["candidates"][1]["document_id"])
            self.assertEqual(selected.status_code, 200)

    def test_unknown_id_returns_404(self):
        self.assertEqual(self.get(document_id="aks:not-found").status_code, 404)

    def test_missing_catalog_is_reported_as_unavailable(self):
        graph = network_runtime._graph_module()
        with patch.object(graph, "catalog", side_effect=FileNotFoundError("manifest")):
            self.assertEqual(self.get(question="경복궁").status_code, 503)


if __name__ == "__main__":
    unittest.main()
