"""Unit tests for Two-tier AI Workflow, Sequence Guardrail, and Sentence Polish View."""

import sys
import unittest
from unittest.mock import MagicMock, patch

from app.core.engine_manager import EngineManager
from app.engines.sentence_polisher import SentenceChange, SentencePolishResult, SentencePolisher
from app.main import QApplication
from app.ui.diff_window import DiffWindow
from app.utils.offline_checker import OfflineSpellChecker

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestSentencePolishAndTwoTierWorkflow(unittest.TestCase):

    def setUp(self):
        # Reset shared offline checker caches for clean test
        OfflineSpellChecker._shared_word_set = None
        OfflineSpellChecker._shared_word_rank = None
        OfflineSpellChecker._shared_phonetic_index = None
        self.checker = OfflineSpellChecker()

    def test_offline_checker_corrects_all_screenshot_critical_typos(self):
        """Verify all critical typos from the user's screenshot are 100% corrected in offline mode."""
        passage = (
            "ইদানিং ছাত্র-ছাত্রীদের মধ্যে লেখা-পড়ার আগ্রহ দিন দিন হ্রাস পাচ্ছে। সরস্বতী পূজায় অঞ্জলী দিয়ে তারা আশির্বাদ "
            "কামনা করে, অথচ নিজেরা নূন্যতম পরিনামেও পরিশ্রম করেনা। পরিক্ষার হলে বসে আকষ্মিক কোনো অলৌকিক সাহায্যের "
            "অপেক্ষা করে। এমন সমিচীন নয় যে শুধু দৈব শক্তির উপর নির্ভর করে পুরস্কার আশা করা যাবে। একটি মুহুর্তের "
            "অসতর্কতা সারাজিবনের কান্নার কারন হতে পারে।"
        )
        result = self.checker.proofread_text(passage)

        self.assertIn("ইদানীং", result)
        self.assertIn("অঞ্জলি", result)
        self.assertIn("আশীর্বাদ", result)
        self.assertIn("ন্যূনতম", result)
        self.assertIn("পরিমাণেও", result)
        self.assertIn("পরীক্ষার", result)
        self.assertIn("আকস্মিক", result)
        self.assertIn("সমীচীন", result)
        self.assertIn("মুহূর্তের", result)
        self.assertIn("সারাজীবনের", result)
        self.assertIn("কারণ", result)

    def test_offline_checker_corrects_muhurther_and_phonetic_aspirations(self):
        """Verify 'মুহুর্থের' and aspirate confusion words are properly detected and corrected offline."""
        passage = "একটি মুহুর্থের অসতর্কতা সারাজিবনের কান্নার কারন হতে পারে।"
        result = self.checker.proofread_text(passage)
        self.assertEqual(result, "একটি মুহূর্তের অসতর্কতা সারাজীবনের কান্নার কারণ হতে পারে।")

        # Test various other forms of মুহূর্ত
        self.assertEqual(self.checker.correct_word("মুহুর্থ"), "মুহূর্ত")
        self.assertEqual(self.checker.correct_word("মুহুর্থে"), "মুহূর্তে")
        self.assertEqual(self.checker.correct_word("মুহুর্থের"), "মুহূর্তের")
        self.assertEqual(self.checker.correct_word("মূহুর্থের"), "মুহূর্তের")
        self.assertEqual(self.checker.correct_word("মুহুর্তের"), "মুহূর্তের")

        # Test aspirate and ba-phala words
        self.assertEqual(self.checker.correct_word("উজ্জল"), "উজ্জ্বল")
        self.assertEqual(self.checker.correct_word("উচ্ছাস"), "উচ্ছ্বাস")
        self.assertEqual(self.checker.correct_word("সান্তনা"), "সান্ত্বনা")
        self.assertEqual(self.checker.correct_word("দ্বন্দ"), "দ্বন্দ্ব")
        self.assertEqual(self.checker.correct_word("কষ্ঠ"), "কষ্ট")
        self.assertEqual(self.checker.correct_word("স্বার্তপর"), "স্বার্থপর")

    def test_sequence_guardrail_blocks_sentence_polish_before_spelling_check(self):
        """Verify clicking 'বাক্য পরিমার্জন' while spelling_checked is False blocks AI and shows warning."""
        engine_mgr = EngineManager(check_network_on_init=False)
        window = DiffWindow(engine_manager=engine_mgr)
        window.orig_edit.setPlainText("এটি একটি পরীক্ষামূলক বাক্য।")

        self.assertFalse(window.spelling_checked)

        with patch("app.ui.diff_window.QMessageBox.exec") as mock_box_exec, \
             patch.object(engine_mgr, "polish_sentences") as mock_polish:
            window.run_sentence_polish()

            # Warning box must be displayed and polish_sentences must NOT be called
            self.assertTrue(mock_box_exec.called)
            mock_polish.assert_not_called()

    def test_sequence_guardrail_allows_sentence_polish_after_spelling_checked(self):
        """Verify spelling_checked becomes True after word-level proofread and resets on edit."""
        engine_mgr = EngineManager(check_network_on_init=False)
        engine_mgr.set_mode("offline")
        window = DiffWindow(engine_manager=engine_mgr)

        window.set_input_text("এটি একটি ভূল বাক্য।")
        # After proofread completes, spelling_checked is True
        self.assertTrue(window.spelling_checked)

        # Modifying text in orig_edit resets spelling_checked to False
        window.orig_edit.setPlainText("নতুন সম্পাদিত বাক্য।")
        self.assertFalse(window.spelling_checked)

    def test_sentence_table_population_and_selective_acceptance(self):
        """Verify dedicated sentence polish view populates table and toggles selections."""
        engine_mgr = EngineManager(check_network_on_init=False)
        window = DiffWindow(engine_manager=engine_mgr)

        dummy_result = SentencePolishResult(
            original_text="তিনি কাজটা করলেন এবং চলে গেলেন।",
            full_polished_text="তিনি কাজটি সম্পন্ন করে প্রস্থান করলেন।",
            changes=[
                SentenceChange(
                    change_id=1,
                    original="তিনি কাজটা করলেন এবং চলে গেলেন।",
                    polished="তিনি কাজটি সম্পন্ন করে প্রস্থান করলেন।",
                    reason="বাক্য গঠন সাবলীলকরণ ও বাহুল্য বর্জন",
                    is_accepted=True
                )
            ]
        )

        window.on_polish_worker_finished(dummy_result)

        # Switched to Tab 3 (Sentence Polish)
        self.assertEqual(window.tabs.currentIndex(), 3)
        self.assertEqual(window.sentence_table.rowCount(), 1)
        self.assertEqual(window.corr_browser.toPlainText().strip(), "তিনি কাজটি সম্পন্ন করে প্রস্থান করলেন।")

        # Reject all sentences
        window.reject_all_sentences()
        self.assertEqual(len(window.accepted_sentence_ids), 0)
        self.assertIn("তিনি কাজটা করলেন এবং চলে গেলেন।", window.corr_browser.toPlainText())

        # Accept all sentences
        window.accept_all_sentences()
        self.assertEqual(len(window.accepted_sentence_ids), 1)
        self.assertIn("তিনি কাজটি সম্পন্ন করে প্রস্থান করলেন।", window.corr_browser.toPlainText())

    def test_sentence_polisher_candidate_models_and_list_response(self):
        """Verify SentencePolisher uses candidate models and handles array/dict responses gracefully."""
        polisher = SentencePolisher(api_key="fake-test-key")
        mock_client = MagicMock()
        polisher.client = mock_client

        # Simulate first model failing with 429 Resource Exhausted, second model succeeding with JSON list
        mock_resp_fail = MagicMock()
        mock_resp_fail.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED Quota exceeded")

        mock_resp_success = MagicMock()
        mock_resp_success.text = (
            '[\n'
            '  {\n'
            '    "original": "তিনি বলিলেন যে যাইবেন।",\n'
            '    "polished": "তিনি বললেন যে যাবেন।",\n'
            '    "reason": "গুরুচণ্ডালী দোষ পরিহার"\n'
            '  }\n'
            ']'
        )

        mock_client.models.generate_content.side_effect = [
            RuntimeError("429 RESOURCE_EXHAUSTED Quota exceeded"),
            mock_resp_success,
        ]

        result = polisher.polish_text("তিনি বলিলেন যে যাইবেন।")
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].polished, "তিনি বললেন যে যাবেন।")
        self.assertEqual(result.changes[0].reason, "গুরুচণ্ডালী দোষ পরিহার")


if __name__ == "__main__":
    unittest.main()
