"""Offline graph regression tests. No env file, network, or DB access."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import heritage_graph as graph


def entry(id, title, field="건축", kind="유적", period="조선"):
    return graph.Entry({"document_id": id, "api_title": title, "api_field": field,
                        "item_type": kind, "period": period})


class NetworkGraphTest(unittest.TestCase):
    def test_request_wording_is_not_a_subject(self):
        book = graph.Catalog([entry('a', '경복궁'), entry('b', '주세')])
        for question in ('경복궁에 대해 알려주세요.', '경복궁을 설명해 주세요', '경복궁을 소개해주세요'):
            self.assertEqual([item.title for item in book.question_candidates(question)], ['경복궁'])
        self.assertEqual(book.resolve_question('주세에 대해 알려주세요').title, '주세')
        book = graph.Catalog([entry('a', '경복궁'), entry('b', '위치'), entry('c', '특징')])
        self.assertEqual(book.resolve_question('경복궁의 위치와 특징은 무엇인가요?').title, '경복궁')

    def test_comparison_keeps_both_subjects(self):
        book = graph.Catalog([entry("a", "경복궁"), entry("b", "창덕궁")])
        self.assertEqual(len(book.question_candidates("경복궁과 창덕궁의 차이")), 2)
        self.assertIsNone(book.resolve_question("경복궁과 창덕궁의 차이"))

    def test_nested_title_is_not_an_extra_subject(self):
        book = graph.Catalog([entry("a", "경복궁"), entry("b", "경복궁 근정전")])
        self.assertEqual(book.resolve_question("경복궁 근정전은?").document_id, "b")
        self.assertEqual(len(book.question_candidates("경복궁과 경복궁 근정전")), 2)

    def test_homonyms_and_citation_fallback_require_choice(self):
        book = graph.Catalog([entry("a", "청자", "미술"), entry("b", "청자", "문학")])
        self.assertEqual(len(book.question_candidates("청자 설명")), 2)
        self.assertEqual(len(book.question_candidates("설명해 줘", ("a", "b", "a"))), 2)

    def test_unrelated_prefix_removed_even_without_same_field_candidate(self):
        book = graph.Catalog([entry("a", "청자", "미술", "개념", "미상"),
                              entry("b", "청자부", "문학", "작품")])
        with patch.object(graph, "catalog", return_value=book):
            result = graph.build_map("a")
        self.assertEqual(result["branches"], [])

    def test_catalog_branches_are_bounded_and_exclude_unknown_period(self):
        items = [entry("root", "유산", period="미상")]
        items += [entry(str(i), f"다른 항목{i}", period="미상") for i in range(20)]
        with patch.object(graph, "catalog", return_value=graph.Catalog(items)):
            result = graph.build_map("root")
        self.assertFalse(any(branch["title"].startswith("시대") for branch in result["branches"]))
        self.assertTrue(all(len(branch["nodes"]) <= 5 for branch in result["branches"]))
        self.assertTrue(result["branches"])

    def test_real_catalog_basic_map_without_external_services(self):
        with patch.object(graph, "build_neighbors", side_effect=AssertionError("external")):
            result = graph.build_map("경복궁", neighbors=None)
        self.assertEqual(result["root"]["title"], "경복궁")
        self.assertTrue(result["branches"])


if __name__ == "__main__":
    unittest.main()
