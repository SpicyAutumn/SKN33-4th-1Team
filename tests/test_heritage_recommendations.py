"""Recommendation policy regression tests, with no external services."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from heritage_graph import Catalog, Entry, catalog
from heritage_recommendations import Recommendations


def entry(id, title, keywords="", kind="문헌"):
    return Entry(dict(document_id=id, api_title=title, keywords=keywords,
                      item_type=kind, period="조선", api_field="역사"))


class RecommendationTest(unittest.TestCase):
    def test_does_not_fill_with_same_era_type_or_title_prefix(self):
        result = Recommendations(Catalog([entry("a", "청자"), entry("b", "가고"),
                                         entry("c", "청자부")])).build("a")
        self.assertEqual(result["branches"], [])

    def test_preserves_person_and_warns_about_homonyms(self):
        result = Recommendations(Catalog([entry("a", "이순신", kind="인물"),
            entry("b", "이순신", kind="인물"), entry("c", "난중일기", "이순신")])).build("a")
        self.assertIn(("유형", "인물"), result["root"]["fields"])
        self.assertIn("같은 이름", result["branches"][0]["note"])
        self.assertEqual(result["branches"][0]["nodes"][0]["document_id"], "c")

    def test_shared_evidence_precedes_alphabetical_order(self):
        result = Recommendations(Catalog([entry("a", "중심", "해전;거북선"),
            entry("b", "가항목", "중심"), entry("c", "하항목", "중심;해전;거북선")])).build("a")
        self.assertEqual(result["branches"][0]["nodes"][0]["document_id"], "c")

    def test_one_shared_keyword_is_not_enough(self):
        result = Recommendations(Catalog([entry("a", "중심", "해전;거북선;조선;왕실"),
            entry("b", "별개", "조선;왕실;해전"), entry("c", "관련", "해전;거북선")])).build("a")
        self.assertEqual([n["title"] for b in result["branches"] for n in b["nodes"]], ["관련"])

    def test_title_reference_precedes_keyword_only_reference(self):
        result = Recommendations(Catalog([entry("a", "이순신"),
            entry("b", "가항목", "이순신"), entry("c", "이순신 난중일기")])).build("a")
        self.assertEqual(result["branches"][0]["nodes"][0]["document_id"], "c")

    def test_unknown_and_bounded_results(self):
        model = Recommendations(Catalog([entry("a", "중심")] +
                                        [entry(str(i), f"자료{i}", "중심") for i in range(10)]))
        self.assertIsNone(model.build("missing"))
        self.assertEqual(len(model.build("a")["branches"][0]["nodes"]), 5)

    def test_real_yi_sun_sin_catalog(self):
        result = Recommendations(catalog()).build("aks:E0044900")
        self.assertIsNotNone(result)
        nodes = [n for branch in result["branches"] for n in branch["nodes"]]
        self.assertTrue(nodes)
        self.assertTrue(all(n["reason"] for n in nodes))
        self.assertFalse(any(n["title"] in ("가", "가고", "가좌책") for n in nodes))
        self.assertIn(("유형", "인물/전통 인물"), result["root"]["fields"])
