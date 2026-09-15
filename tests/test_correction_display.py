"""Offline UI-call tests; no Streamlit server, model or speech playback."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class CorrectionDisplayTest(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "app/components/response_cards.py"
        spec = importlib.util.spec_from_file_location("isolated_response_cards", path)
        self.cards = importlib.util.module_from_spec(spec)
        self.st = Mock()
        with patch.dict("sys.modules", {"streamlit": self.st, "rag_client": Mock()}):
            spec.loader.exec_module(self.cards)
        self.cards._listen_button = Mock()

    def render(self, summary, message):
        response = {"response_type": "corrected_premise", "message": message,
                    "premise_correction": {"corrected_premise": summary}}
        before = deepcopy(response)
        self.cards.render(response)
        self.assertEqual(response, before)

    def test_distinct_summary_and_full_message_in_order(self):
        self.render("2002년입니다.", "2001년이 아니라 2002년입니다.")
        self.assertEqual(self.st.write.call_args_list, [(("2002년입니다.",),), (("2001년이 아니라 2002년입니다.",),)])
        self.cards._listen_button.assert_called_once_with("correction", "2002년입니다.\n\n2001년이 아니라 2002년입니다.")

    def test_identical_text_once(self):
        self.render("정정 설명", "정정 설명")
        self.st.write.assert_called_once_with("정정 설명")
        self.cards._listen_button.assert_called_once_with("correction", "정정 설명")

    def test_partial_overlap_and_long_message_preserved(self):
        message = "정정 설명. " + "추가 설명. " * 500
        self.render("정정 설명.", message)
        self.assertEqual(self.st.write.call_args_list[-1].args, (message,))
        self.cards._listen_button.assert_called_once_with("correction", "정정 설명.\n\n" + message)
        self.st.expander.assert_not_called()

    def test_whitespace_difference_is_not_exact_duplicate(self):
        self.render("정정 설명", " 정정 설명 ")
        self.assertEqual(self.st.write.call_count, 2)

    def test_invalid_summary_falls_back_to_message(self):
        for summary in (None, "", "  ", 42):
            with self.subTest(summary=summary):
                self.st.reset_mock()
                self.cards._listen_button.reset_mock()
                self.render(summary, "전체 설명")
                self.st.write.assert_called_once_with("전체 설명")
                self.cards._listen_button.assert_called_once_with("correction", "전체 설명")

    def test_missing_correction_object(self):
        self.cards.render({"response_type": "corrected_premise", "message": "전체 설명"})
        self.st.write.assert_called_once_with("전체 설명")

    def test_summary_only_and_no_text(self):
        self.render("정정 설명", None)
        self.st.write.assert_called_once_with("정정 설명")
        self.st.reset_mock()
        self.cards._listen_button.reset_mock()
        self.render(None, " ")
        self.st.write.assert_not_called()
        self.st.warning.assert_called_once()
        self.cards._listen_button.assert_not_called()

    def test_normal_answer_unchanged(self):
        self.cards.render({"response_type": "answered", "message": "정상 답변"})
        self.st.write.assert_called_once_with("정상 답변")
        self.cards._listen_button.assert_called_once_with("answer", "정상 답변")
