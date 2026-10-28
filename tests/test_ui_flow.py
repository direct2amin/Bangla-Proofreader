"""Functional UI test for DiffWindow selective change management and i18n."""

import os
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.main import QApplication
from app.ui.diff_window import DiffWindow
from app.core.engine_manager import EngineManager
from app.utils.diff_highlighter import DiffHighlighter


class TestDiffWindowUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selective_changes(self):
        engine_mgr = EngineManager()
        window = DiffWindow(engine_manager=engine_mgr)

        orig = "আগামি কালকে আমরা গুরুত্বপূর্ন মিটিং করব।"
        corr = "আগামীকাল আমরা গুরুত্বপূর্ণ মিটিং করব।"

        diff_res = DiffHighlighter.compute_diff(orig, corr)
        window.last_diff_result = diff_res
        window.accepted_change_ids = {c.change_id for c in diff_res.changes}
        window.populate_changes_table(diff_res)
        window.refresh_views()

        # Both changes initially accepted
        full_corr = window.get_corrected_text()
        self.assertIn("আগামীকাল", full_corr)
        self.assertIn("গুরুত্বপূর্ণ", full_corr)

        # Reject change 0 ("আগামি কালকে" -> "আগামীকাল")
        window.on_change_toggled(0, False)
        partial_corr = window.get_corrected_text()
        self.assertIn("আগামি কালকে", partial_corr)
        self.assertIn("গুরুত্বপূর্ণ", partial_corr)

        # Reject all changes
        window.reject_all_changes()
        rejected_corr = window.get_corrected_text()
        self.assertEqual(rejected_corr, orig)

        # Accept all changes
        window.accept_all_changes()
        accepted_corr = window.get_corrected_text()
        self.assertEqual(accepted_corr, corr)

    def test_language_toggle(self):
        engine_mgr = EngineManager()
        window = DiffWindow(engine_manager=engine_mgr)

        # Default is English
        self.assertEqual(window.lang, "en")
        self.assertEqual(window.proofread_btn.text(), "Word Proofread (AI)")
        self.assertEqual(window.polish_btn.text(), "Sentence Polish (AI)")
        self.assertEqual(window.paste_btn.text(), "Paste")

        # Toggle to Bangla
        window.toggle_language()
        self.assertEqual(window.lang, "bn")
        self.assertEqual(window.proofread_btn.text(), "শব্দ প্রুফরিড (AI Proofread)")
        self.assertEqual(window.polish_btn.text(), "বাক্য পরিমার্জন (AI Sentence Polish)")
        self.assertEqual(window.paste_btn.text(), "পেস্ট করুন")

        # Toggle back to English
        window.toggle_language()
        self.assertEqual(window.lang, "en")
        self.assertEqual(window.proofread_btn.text(), "Word Proofread (AI)")
        self.assertEqual(window.polish_btn.text(), "Sentence Polish (AI)")

    def test_left_red_marks_and_identical_line_spacing(self):
        engine_mgr = EngineManager()
        window = DiffWindow(engine_manager=engine_mgr)
        window.apply_theme("light")

        orig = "প্রথম লাইনে কোনো ভুল নেই।\nদ্বিতীয় লাইনে গুরুত্বপূর্ন কথা আছে।\nতৃতীয় লাইনে বানান ভুল আছে।"
        corr = "প্রথম লাইনে কোনো ভুল নেই।\nদ্বিতীয় লাইনে গুরুত্বপূর্ণ কথা আছে।\nতৃতীয় লাইনে বানান শুদ্ধ আছে।"

        window._set_orig_plain_text(orig)
        diff_res = DiffHighlighter.compute_diff(orig, corr, is_dark=False)
        window.on_worker_finished(corr, diff_res)

        orig_html = window.orig_edit.toHtml().lower()
        corr_html = window.corr_browser.toHtml().lower()

        # Left panel has red highlight background (#fee2e2) and right panel has green (#dcfce7)
        self.assertIn("#fee2e2", orig_html)
        self.assertIn("#dcfce7", corr_html)

        # Verify line spacing block format (135% proportional height) matches in both panels
        orig_fmt = window.orig_edit.document().begin().blockFormat()
        corr_fmt = window.corr_browser.document().begin().blockFormat()
        self.assertEqual(orig_fmt.lineHeight(), 135.0)
        self.assertEqual(corr_fmt.lineHeight(), 135.0)
        self.assertEqual(orig_fmt.topMargin(), 0.0)
        self.assertEqual(corr_fmt.topMargin(), 0.0)
        self.assertEqual(orig_fmt.bottomMargin(), 0.0)
        self.assertEqual(corr_fmt.bottomMargin(), 0.0)

        # Verify bottom-left shortcut status label remains visible even after proofreading finishes
        self.assertTrue(hasattr(window, "shortcut_status_label"))
        window.update_shortcut_status("ctrl+alt+x")
        self.assertIn("Ctrl+Alt+X", window.shortcut_status_label.text())
        window.on_worker_finished(corr, diff_res)
        self.assertIn("Ctrl+Alt+X", window.shortcut_status_label.text())


if __name__ == "__main__":
    unittest.main()
