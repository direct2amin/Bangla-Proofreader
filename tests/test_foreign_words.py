"""Tests for foreign/Arabic word detection, exclusion, punctuation formatting, About dialog, and assets."""

import os
import unittest
from app.utils.foreign_words import is_foreign_word, is_arabic_word, get_word_classification
from app.utils.diff_highlighter import DiffHighlighter
from app.utils.punctuation_formatter import format_bangla_punctuation
from app.engines.gemini_engine import preserve_line_structure, sanitize_arabic_and_hybrid_tokens
from app.ui.api_guide_dialog import ApiGuideDialog
from app.ui.about_dialog import AboutDialog
from app.ui.diff_window import DiffWindow, LOGO_BANNER_PATH, LOGO_ICON_PATH
from app.core.engine_manager import EngineManager
from app.main import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestForeignWords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_foreign_and_arabic_word_detector(self):
        # Arabic/Islamic words with variations
        self.assertTrue(is_arabic_word("হাদীস", "হাদিস"))
        self.assertTrue(is_arabic_word("নামায", "নামাজ"))
        self.assertTrue(is_arabic_word("রোযা", "রোজা"))
        self.assertTrue(is_arabic_word("রমযান", "রমজান"))
        self.assertTrue(is_arabic_word("কুরআন", "কোরআন"))
        self.assertTrue(is_arabic_word("শহীদ", "শহিদ"))

        # User specified words: iman, ibadat
        self.assertTrue(is_arabic_word("ইমান", "ঈমান"))
        self.assertTrue(is_arabic_word("ঈমানের", "ইমানের"))
        self.assertTrue(is_arabic_word("এবাদত", "ইবাদত"))
        self.assertTrue(is_arabic_word("এবাদতের", "ইবাদতের"))
        self.assertTrue(is_arabic_word("হজ্জ্ব যাত্রীদের", "হজযাত্রীদের"))
        self.assertTrue(is_arabic_word("মুফতী", "মুফতি"))
        self.assertTrue(is_arabic_word("তাক্বওয়া", "তাকওয়া"))
        self.assertTrue(is_arabic_word("যাকাত", "জাকাত"))
        self.assertTrue(is_arabic_word("সাদাকা", "সদকা"))
        self.assertTrue(is_arabic_word("মুনাজাত", "মোনাজাত"))

        # Newly expanded terms from user's test text
        self.assertTrue(is_arabic_word("তালিবুল ইলেম", "তালিবে ইলম"))
        self.assertTrue(is_arabic_word("তালেবে এলেম", "তালিবে ইলম"))
        self.assertTrue(is_arabic_word("উস্তাদের", "উস্তাযের"))
        self.assertTrue(is_arabic_word("আসাতিযায়ে কেরামের", "আসাতেজায়ে কেরামের"))
        self.assertTrue(is_arabic_word("তাআলা", "তাআলা"))
        self.assertTrue(is_arabic_word("আমিন", "আমীন"))
        self.assertTrue(is_arabic_word("আকিদা", "আক্বীদা"))
        self.assertTrue(is_arabic_word("মুমিনের", "মুমিনের"))
        self.assertTrue(is_arabic_word("এলেম চর্চার", "ইলম চর্চার"))
        self.assertTrue(is_arabic_word("نحمده ونصلى", "نحمده ونصلي"))

        # Classification check
        self.assertEqual(get_word_classification("হাদীস", "হাদিস"), "arabic")
        self.assertEqual(get_word_classification("উস্তাদের", "উস্তাযের"), "arabic")
        self.assertEqual(get_word_classification("المتن", "المتن"), "arabic")
        self.assertEqual(get_word_classification("ষ্টেশন", "স্টেশন"), "foreign")
        self.assertEqual(get_word_classification("কর্মচারিদের", "কর্মচারীদের"), "native")
        self.assertEqual(get_word_classification("সংংশ্লিষ্ট", "সংশ্লিষ্ট"), "native")
        self.assertEqual(get_word_classification("সংশ্লিষ্ট", "সংশ্লিষ্ট"), "native")
        self.assertEqual(get_word_classification("বিশিষ্ট", "বিশিষ্ট"), "native")
        self.assertEqual(get_word_classification("নির্দিষ্ট", "নির্দিষ্ট"), "native")
        self.assertEqual(get_word_classification("উপকারী", "উপকারী"), "native")
        self.assertEqual(get_word_classification("আবেদনকারী", "আবেদনকারী"), "native")

        # English loanwords
        self.assertTrue(is_foreign_word("ষ্টেশন", "স্টেশন"))
        self.assertTrue(is_foreign_word("ডিগ্রী", "ডিগ্রি"))

        # Native/Tatsama Bengali words (NOT foreign)
        self.assertFalse(is_foreign_word("সংংশ্লিষ্ট", "সংশ্লিষ্ট"))
        self.assertFalse(is_foreign_word("সংশ্লিষ্ট", "সংশ্লিষ্ট"))
        self.assertFalse(is_foreign_word("বিশিষ্ট", "বিশিষ্ট"))
        self.assertFalse(is_foreign_word("নির্দিষ্ট", "নির্দিষ্ট"))
        self.assertFalse(is_foreign_word("উপকারী", "উপকারী"))
        self.assertFalse(is_foreign_word("আবেদনকারী", "আবেদনকারী"))
        self.assertFalse(is_foreign_word("কর্মচারিদের", "কর্মচারীদের"))
        self.assertFalse(is_foreign_word("গ্রহন", "গ্রহণ"))
        self.assertFalse(is_foreign_word("গুরুত্বপূর্ন", "গুরুত্বপূর্ণ"))
        self.assertFalse(is_foreign_word("আলোচনা সভা", "আলোচনাসভা"))
        self.assertFalse(is_foreign_word("শুধুমাত্র", "শুধু"))

    def test_exclude_arabic_words_ui(self):
        engine_mgr = EngineManager()
        window = DiffWindow(engine_manager=engine_mgr)

        orig = "তিনি হাদীস পড়েন, এবাদত করেন, উস্তাদের দোয়া চান এবং কর্মচারিদের অবহেলা করেন।"
        corr = "তিনি হাদিস পড়েন, ইবাদত করেন, উস্তাযের দোয়া চান এবং কর্মচারীদের অবহেলা করেন।"

        diff_res = DiffHighlighter.compute_diff(orig, corr)
        window.last_diff_result = diff_res
        window.accepted_change_ids = {c.change_id for c in diff_res.changes}
        window.populate_changes_table(diff_res)
        window.refresh_views()

        # Before exclusion: "হাদিস", "ইবাদত", "উস্তাযের", and "কর্মচারীদের" all accepted
        self.assertIn("হাদিস", window.get_corrected_text())
        self.assertIn("ইবাদত", window.get_corrected_text())
        self.assertIn("উস্তাযের", window.get_corrected_text())
        self.assertIn("কর্মচারীদের", window.get_corrected_text())

        # Click Exclude Arabic Words
        window.exclude_foreign_words()

        # After exclusion: "হাদীস", "এবাদত", "উস্তাদের" (original) preserved, while "কর্মচারীদের" remains corrected!
        corrected_text = window.get_corrected_text()
        self.assertIn("হাদীস", corrected_text)
        self.assertIn("এবাদত", corrected_text)
        self.assertIn("উস্তাদের", corrected_text)
        self.assertIn("কর্মচারীদের", corrected_text)

    def test_punctuation_formatter_utility(self):
        raw = "তিনি আসবেন .আমরা যাবো । সেখানে সভা হবে ,, মানুষ আসবে ,কথা শুনবে।"
        corr = format_bangla_punctuation(raw)
        self.assertIn("আসবেন। আমরা", corr)
        self.assertIn("যাবো। সেখানে", corr)
        self.assertIn("হবে, মানুষ", corr)
        self.assertIn("আসবে, কথা", corr)

    def test_nfc_normalization_and_no_identical_suggestions(self):
        import unicodedata
        # NFD vs NFC decomposed variations
        orig = "চেতনার দাওরায়ে জামিয়ার বিদায়ী প্রিয়"
        corr = unicodedata.normalize('NFD', orig)
        res = DiffHighlighter.compute_diff(orig, corr)
        # Should NOT produce any false suggestions where original == suggested
        self.assertEqual(len(res.changes), 0)

        # Word with whitespace shift should not suggest same word
        res2 = DiffHighlighter.compute_diff("চেতনার", "চেতনার ")
        for chg in res2.changes:
            if chg.original.strip() or chg.corrected.strip():
                self.assertNotEqual(chg.original.strip(), chg.corrected.strip())

    def test_preserve_line_structure(self):
        orig = "লাইন ১\nলাইন ২\nলাইন ৩"
        corr_with_extra_blanks = "লাইন ১\n\nলাইন ২\n\nলাইন ৩"
        result = preserve_line_structure(orig, corr_with_extra_blanks)
        self.assertEqual(result, "লাইন ১\nলাইন ২\nলাইন ৩")

    def test_arabic_script_hybrid_sanitizer(self):
        # Case where Gemini mixed Arabic letters and Bengali letters into a hybrid token
        orig = "কিতাবের নাম المتن এবং সংংশ্লিষ্ট বিষয়।"
        corrupted = "কিতাবের নাম المتত্ন এবং সংশ্লিষ্ট বিষয়।"
        fixed = sanitize_arabic_and_hybrid_tokens(orig, corrupted)
        self.assertIn("المتن", fixed)
        self.assertNotIn("المত্ন", fixed)
        self.assertEqual(fixed, "কিতাবের নাম المتن এবং সংশ্লিষ্ট বিষয়।")

    def test_about_dialog_ui_and_portfolio_link(self):
        from app.ui.about_dialog import PORTFOLIO_URL
        self.assertEqual(PORTFOLIO_URL, "https://direct2amin.github.io/aminsweb/")

        dlg_en = AboutDialog(lang="en")
        self.assertEqual(dlg_en.windowTitle(), "About Bangla Proofreader")
        self.assertGreaterEqual(dlg_en.minimumWidth(), 540)

        dlg_bn = AboutDialog(lang="bn")
        # English title to prevent Windows title bar tofu boxes
        self.assertEqual(dlg_bn.windowTitle(), "About Bangla Proofreader")

    def test_api_guide_dialog_copy_link(self):
        from app.ui.api_guide_dialog import AI_STUDIO_URL
        from app.core.clipboard import ClipboardManager
        dlg = ApiGuideDialog(lang="en")
        self.assertTrue(hasattr(dlg, "url_btn"))
        self.assertTrue(hasattr(dlg, "copy_link_btn"))
        dlg.copy_ai_studio_link()
        self.assertEqual(ClipboardManager.get_text(), AI_STUDIO_URL)
        self.assertIn("Copied", dlg.copy_link_btn.text())

    def test_default_bangla_font(self):
        from app.ui.diff_window import BANGLA_FONT
        self.assertTrue("Bornomala" in BANGLA_FONT or "Nirmala UI" in BANGLA_FONT)

    def test_logo_assets_and_tray_icon_exist(self):
        from app.main import TRAY_ICON_PATH
        self.assertTrue(os.path.exists(LOGO_ICON_PATH), f"Missing {LOGO_ICON_PATH}")
        self.assertTrue(os.path.exists(LOGO_BANNER_PATH), f"Missing {LOGO_BANNER_PATH}")
        self.assertTrue(os.path.exists(TRAY_ICON_PATH), f"Missing {TRAY_ICON_PATH}")

    def test_format_punct_btn_removed(self):
        engine_mgr = EngineManager()
        window = DiffWindow(engine_manager=engine_mgr)
        self.assertFalse(hasattr(window, "format_punct_btn"))
        # Verify window title remains English to prevent tofu boxes
        window.lang = "bn"
        window.apply_language()
        self.assertEqual(window.windowTitle(), "Bangla Proofreader")

    def test_bd_gazetteer_and_anti_prompt_injection_guards(self):
        from app.utils.bd_gazetteer import get_geo_reference_for_text
        from app.engines.gemini_engine import (
            is_conversational_hallucination,
            strip_wrapper_tags_and_fences,
        )

        # Gazetteer should detect Trishal Thana and provide আউলটিয়া and চকপাঁচপাড়া
        import unicodedata
        sample = "গ্রাম: আউটিয়া, ডাক: চকপাঁচপারা\nথানা: ত্রিশাল, জেলা: ময়মনসিংহ"
        geo_ref = unicodedata.normalize("NFC", get_geo_reference_for_text(sample))
        self.assertIn("ত্রিশাল", geo_ref)
        self.assertIn(unicodedata.normalize("NFC", "আউলটিয়া"), geo_ref)
        self.assertIn(unicodedata.normalize("NFC", "চকপাঁচপাড়া"), geo_ref)

        # Conversational hallucination guard should catch chatbot replies
        orig = "ঠিক ভাবে কাজ করছে না।\nএখানে একটা ঠিক করতে পেরেছে আরেকটি ঠিক করতে পারেনি।"
        bad_reply = "আপনার প্রতিক্রিয়ার জন্য ধন্যবাদ। আমি বিষয়টি লক্ষ্য করেছি।\nসঠিক রূপটি হলো: গ্রাম: আউলটিয়া"
        self.assertTrue(is_conversational_hallucination(orig, bad_reply))

        good_reply = "ঠিকভাবে কাজ করছে না।\nএখানে একটা ঠিক করতে পেরেছে আরেকটি ঠিক করতে পারেনি।"
        self.assertFalse(is_conversational_hallucination(orig, good_reply))

        # Wrapper tag stripper
        wrapped = "<text_to_proofread>\nঠিকভাবে কাজ করছে না।\n</text_to_proofread>"
        self.assertEqual(strip_wrapper_tags_and_fences(wrapped), "ঠিকভাবে কাজ করছে না।")


if __name__ == "__main__":
    unittest.main()
