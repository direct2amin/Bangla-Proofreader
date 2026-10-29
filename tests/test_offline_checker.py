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

    def test_ui_offline_bijoy_conversion_on_input(self):
        """Verify that Bijoy text input is instantly auto-converted to Unicode, and mode_combo is removed."""
        engine_mgr = EngineManager(check_network_on_init=False)
        window = DiffWindow(engine_manager=engine_mgr)
        window.lang = "en"
        window.apply_language()

        # Offline mode selector combobox must not exist in UI
        self.assertFalse(hasattr(window, "mode_combo"))

        bijoy_sample = "Avgvi †mvbvi evsjv| Avwg †Zvgvq fv‡jvevwm|"
        with patch.object(window, "run_proofread"):
            window.set_input_text(bijoy_sample)

        self.assertEqual(
            unicodedata.normalize("NFC", window._get_orig_plain_text().strip()),
            unicodedata.normalize("NFC", "আমার সোনার বাংলা। আমি তোমায় ভালোবাসি।")
        )

    def test_proofread_warns_when_no_internet(self):
        """Verify app displays warning gracefully without crashing when PC has no internet connection."""
        engine_mgr = EngineManager(check_network_on_init=False)
        window = DiffWindow(engine_manager=engine_mgr)

        with patch.object(EngineManager, "is_internet_available", return_value=False), \
             patch("app.ui.diff_window.show_themed_message_box") as mock_msg:
            window.set_input_text("এটি একটি বাংলা বাক্য।")
            mock_msg.assert_called_once()

    def test_morphological_stemming_and_reinflection_engine(self):
        """Verify decompose_word, root correction, and suffix re-attachment."""
        # 1. decompose_word
        self.assertEqual(self.checker.decompose_word("খুতবা"), ("খুতবা", ""))
        self.assertEqual(self.checker.decompose_word("খুতবায়"), ("খুতবায়", ""))
        self.assertEqual(self.checker.decompose_word("লাইব্রেরীর"), ("লাইব্রেরী", "র"))
        self.assertEqual(self.checker.decompose_word("লাইব্রেরীতে"), ("লাইব্রেরী", "তে"))
        self.assertEqual(self.checker.decompose_word("ছাত্রদেরকে"), ("ছাত্র", "দেরকে"))

        # 2. Root Correction & Re-inflection:
        # "লাইব্রেরীর" -> root "লাইব্রেরী" corrected to "লাইব্রেরি" + suffix "র" = "লাইব্রেরির"
        self.assertFalse(self.checker.is_valid_word("লাইব্রেরীর"))
        self.assertEqual(self.checker.suggest("লাইব্রেরীর"), ["লাইব্রেরির"])
        self.assertEqual(self.checker.correct_word("লাইব্রেরীর"), "লাইব্রেরির")

        # "লাইব্রেরীতে" -> "লাইব্রেরিতে"
        self.assertEqual(self.checker.correct_word("লাইব্রেরীতে"), "লাইব্রেরিতে")

        # "পরিক্ষায়" -> "পরীক্ষায়"
        self.assertEqual(self.checker.correct_word("পরিক্ষায়"), "পরীক্ষায়")

        # "ভূলগুলো" -> "ভুলগুলো"
        self.assertEqual(self.checker.correct_word("ভূলগুলো"), "ভুলগুলো")

        # "সহযোগীতায়" -> "সহযোগিতায়"
        self.assertEqual(self.checker.correct_word("সহযোগীতায়"), "সহযোগিতায়")

        # Step A safeguards: valid inflected words kept completely unchanged
        self.assertTrue(self.checker.is_valid_word("ছাত্রদেরকে"))
        self.assertEqual(self.checker.correct_word("ছাত্রদেরকে"), "ছাত্রদেরকে")
        self.assertTrue(self.checker.is_valid_word("খুতবায়"))
        self.assertEqual(self.checker.correct_word("খুতবায়"), "খুতবায়")
        self.assertTrue(self.checker.is_valid_word("রুজির"))
        self.assertEqual(self.checker.correct_word("রুজির"), "রুজির")

    def test_unrecognized_words_never_falsely_replaced(self):
        """Verify that unrecognized proper names, cultural or novel Bengali words are NEVER replaced with false dictionary words."""
        test_words = [
            "শাকেরের", "মুফাসসিরিন", "আব্দুল্লাহ", "হাওলাদার", "চাকলাদার",
            "তানভীর", "রুজির", "খুতবায়", "মোসাদ্দেক", "তাহমিনা"
        ]
        for w in test_words:
            # Word must be preserved untouched by correct_word
            self.assertEqual(
                self.checker.correct_word(w), w,
                f"Word '{w}' was falsely converted to '{self.checker.correct_word(w)}'"
            )

    def test_window_titles_never_contain_bengali(self):
        """Verify all window and dialog titles in both English and Bangla locales contain zero Bengali characters."""
        import re
        from app.utils.i18n import MESSAGES
        bangla_re = re.compile(r"[\u0980-\u09FF]")

        for lang in ("en", "bn"):
            for key, val in MESSAGES[lang].items():
                if key.endswith("_title") and isinstance(val, str):
                    self.assertIsNone(
                        bangla_re.search(val),
                        f"Title key '{key}' in locale '{lang}' has Bengali characters: '{val}'"
                    )

    def test_gemini_models_list_and_fast_defaults(self):
        """Verify Gemini engine uses official fast models and does not use non-existent models."""
        from app.engines.gemini_engine import GeminiProofreaderEngine
        engine = GeminiProofreaderEngine(api_key="test-key")
        self.assertEqual(engine.model_name, "gemini-3.5-flash-lite")

    def test_parshe_corrected_to_parshwe_not_purse(self):
        """Verify 'পার্শে' is accurately corrected to 'পার্শ্বে' and never to 'পার্সে'."""
        self.assertEqual(self.checker.correct_word("পার্শে"), "পার্শ্বে")
        self.assertEqual(self.checker.suggest("পার্শে"), ["পার্শ্বে"])
        self.assertNotIn("পার্সে", self.checker.suggest("পার্শে"))

    def test_traditional_ee_kar_and_uporokto_preserved(self):
        """Verify traditional -ী spellings (দেওবন্দী, মাদানী, আসমানী, উত্তরসূরী, বিধানাবলী) and উপরোক্ত are preserved."""
        for w in ["দেওবন্দী", "দেওবন্দি", "মাদানী", "মাদানি", "আসমানী", "আসমানি", "উত্তরসূরী", "উত্তরসূরি", "বিধানাবলী", "বিধানাবলি", "উপরোক্ত", "উপর্যুক্ত"]:
            self.assertTrue(self.checker.is_valid_word(w), f"Word '{w}' was unexpectedly marked invalid")
            self.assertEqual(self.checker.correct_word(w), w, f"Word '{w}' was unexpectedly modified to '{self.checker.correct_word(w)}'")

    def test_bijoy_converter_protects_unicode_text(self):
        """Verify convert_bijoy_to_unicode leaves Unicode text 100% untouched to prevent character corruption."""
        from app.utils.bijoy_converter import convert_bijoy_to_unicode, is_unicode_bengali_text
        unicode_sample = "সহপাঠীদের সাথে কাটানো সোনালী স্মৃতিগুলো হৃদয়ে গেঁথে থাকবে।"
        self.assertTrue(is_unicode_bengali_text(unicode_sample))
        self.assertEqual(convert_bijoy_to_unicode(unicode_sample), unicode_sample)

    def test_progress_bar_in_status_bar_not_toolbar(self):
        """Verify progress bar and label are placed in bottom status bar, avoiding toolbar collision."""
        window = DiffWindow()
        self.assertIs(window.progress_bar.parent(), window.status_bar)
        self.assertIs(window.progress_log_lbl.parent(), window.status_bar)
        self.assertIs(window.shortcut_status_label.parent(), window.status_bar)


if __name__ == "__main__":
    unittest.main()
