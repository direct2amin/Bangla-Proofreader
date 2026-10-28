"""Unit tests for Conservative Offline Spell Checker, Suffix Stemming, Islamic Vocab, and Auto-Offline Fallback."""

import os
import sys
import time
import unicodedata
import unittest
from unittest.mock import patch

from app.core.engine_manager import EngineManager
from app.main import QApplication
from app.ui.diff_window import DiffWindow
from app.utils.offline_checker import OfflineSpellChecker, levenshtein_distance

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestOfflineCheckerAndModeSwitcher(unittest.TestCase):

    def setUp(self):
        self.checker = OfflineSpellChecker()

    def test_dictionary_loaded_over_100k_words(self):
        self.assertTrue(os.path.exists(self.checker.dict_path), f"Missing {self.checker.dict_path}")
        self.assertGreaterEqual(len(self.checker.word_set), 100000)

    def test_no_aggressive_false_replacements_and_islamic_vocab(self):
        """Verify screenshot passage: রুজির != রুচির, খুতবায় != খুতবা, খুৎবার != খুতবা."""
        passage = (
            "সর্বদা জুমার খুতবায় থাকতে হবে। যদি খুৎবার জন্য ডাক না আসে তবে বলে-কয়ে হলেও নিতে হবে। "
            "এতে কয়েকটা উপকারিতা রয়েছে :\n"
            "ক. ইলিমের চর্চা থাকবে। কুরআন হাদিসের সাথে সম্পর্ক থাকবে।\n"
            "খ. দাওয়াতী কাজের হক আদায় হবে।\n"
            "গ. কিছু রুটি রুজির ব্যবস্থাও হবে।\n"
            "কোনভাবেই সামাজিক কাজে জড়িয়ে পড়া যাবে না।"
        )
        result = self.checker.proofread_text(passage)
        self.assertIn("খুতবায়", result)
        self.assertIn("খুৎবার", result)
        self.assertIn("ইলিমের", result)
        self.assertIn("দাওয়াতী", result)
        self.assertIn("রুজির", result)
        self.assertNotIn("রুচির", result)

    def test_bengali_stemming_and_suffix_handling(self):
        """Verify inflected words with ['র', 'ের', 'য়', 'ে', 'তে', 'কে', 'রা', 'দের', 'গুলো', 'খানি', 'টা', 'টি'] are valid."""
        inflected_words = [
            "খুতবায়", "খুতবার", "ইলমের", "রুজির", "মসজিদে", "মাদ্রাসাতে",
            "আলেমদের", "কিতাবগুলো", "বইখানি", "কলমটা", "মানুষটি", "ছাত্ররা", "শিক্ষককে"
        ]
        for w in inflected_words:
            self.assertTrue(self.checker.is_valid_word(w), f"Inflected word '{w}' should be valid via suffix stemming")
            self.assertEqual(self.checker.correct_word(w), w, f"Inflected word '{w}' must remain untouched")

    def test_conservative_edit_distance_1_threshold(self):
        t0 = time.perf_counter()
        self.assertEqual(self.checker.correct_word("ভূল"), "ভুল")
        self.assertEqual(self.checker.correct_word("পরিক্ষা"), "পরীক্ষা")
        self.assertEqual(self.checker.correct_word("পুরুস্কার"), "পুরস্কার")
        self.assertEqual(self.checker.correct_word("বিতরন"), "বিতরণ")
        self.assertEqual(self.checker.correct_word("তামায়"), "তোমায়")
        # Stem + Suffix correction preserves suffix ('পরিক্ষা' + 'য়' -> 'পরীক্ষায়')
        self.assertEqual(self.checker.correct_word("পরিক্ষায়"), "পরীক্ষায়")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 50.0)

        self.assertEqual(levenshtein_distance("তামায়", "তোমায়"), 1)
        self.assertGreater(levenshtein_distance("বাংলাদেশ", "আন্তর্জাতিক", max_dist=1), 1)

    def test_ui_mode_switcher_and_offline_bijoy_pipeline(self):
        engine_mgr = EngineManager(check_network_on_init=False)
        engine_mgr.set_mode("offline")
        window = DiffWindow(engine_manager=engine_mgr)
        window.lang = "en"
        window.apply_language()

        self.assertEqual(window.mode_combo.count(), 2)
        self.assertEqual(window.mode_combo.itemText(0), "Offline (Local Dictionary- Instant)")
        self.assertEqual(window.mode_combo.itemText(1), "Online AI (Gemini AI - Contextual)")
        self.assertEqual(window.mode_combo.currentData(), "offline")

        bijoy_with_typo = "Avgvi †mvbvi evsjv| Avwg Zvgvq fv‡jvevwm|"
        window.set_input_text(bijoy_with_typo)

        self.assertEqual(
            unicodedata.normalize("NFC", window._get_orig_plain_text().strip()),
            unicodedata.normalize("NFC", "আমার সোনার বাংলা। আমি তামায় ভালোবাসি।")
        )
        self.assertIsNotNone(window.last_diff_result)
        self.assertEqual(
            unicodedata.normalize("NFC", window.corr_browser.toPlainText().strip()),
            unicodedata.normalize("NFC", "আমার সোনার বাংলা। আমি তোমায় ভালোবাসি।")
        )
        self.assertEqual(window.changes_table.rowCount(), 1)
        engine_mgr.set_mode("online")

    def test_auto_offline_fallback_when_no_internet(self):
        """Verify app automatically switches to Offline Mode when PC has no internet connection."""
        engine_mgr = EngineManager(check_network_on_init=False)
        engine_mgr.set_mode("online")
        window = DiffWindow(engine_manager=engine_mgr)
        self.assertEqual(window.mode_combo.currentData(), "online")

        with patch.object(EngineManager, "is_internet_available", return_value=False):
            window.set_input_text("এটি একটি ভূল বানান।")
            # Must automatically switch to offline mode and complete proofreading
            self.assertEqual(engine_mgr.get_mode(), "offline")
            self.assertEqual(window.mode_combo.currentData(), "offline")
            self.assertEqual(
                unicodedata.normalize("NFC", window.corr_browser.toPlainText().strip()),
                unicodedata.normalize("NFC", "এটি একটি ভুল বানান।")
            )

        engine_mgr.set_mode("online")


if __name__ == "__main__":
    unittest.main()
