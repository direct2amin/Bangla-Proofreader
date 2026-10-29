"""Functional UI test for DiffWindow selective change management and i18n."""

import os
import unittest
from unittest.mock import patch

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
        with patch("app.ui.diff_window.load_config", return_value={"ui_language": "en"}):
            window = DiffWindow(engine_manager=engine_mgr)

        # Default is English
        self.assertEqual(window.lang, "en")
        self.assertEqual(window.proofread_btn.text(), "Proofread")
        self.assertEqual(window.polish_btn.text(), "Sentence Polish")
        self.assertEqual(window.paste_btn.text(), "Paste")

        # Toggle to Bangla
        window.toggle_language()
        self.assertEqual(window.lang, "bn")
        self.assertEqual(window.proofread_btn.text(), "প্রুফরিড")
        self.assertEqual(window.polish_btn.text(), "বাক্য পরিমার্জন")
        self.assertEqual(window.paste_btn.text(), "পেস্ট")

        # Toggle back to English
        window.toggle_language()
        self.assertEqual(window.lang, "en")
        self.assertEqual(window.proofread_btn.text(), "Proofread")
        self.assertEqual(window.polish_btn.text(), "Sentence Polish")

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

    def test_compact_model_combobox_and_modern_checkboxes(self):
        from app.ui.settings_dialog import CompactModelComboBox, SettingsDialog
        from app.core.theme import get_settings_stylesheet, get_window_stylesheet
        from app.core.config import DEFAULT_CONFIG

        combo = CompactModelComboBox()
        combo.addItem("gemini-3.5-flash-lite (Ultra-fast ~0.8s - Recommended)", "gemini-3.5-flash-lite")
        combo.addItem("gemini-3.5-flash (High Accuracy ~3s)", "gemini-3.5-flash")

        # Size hints remain compact
        sz = combo.sizeHint()
        self.assertLessEqual(sz.width(), 260)

        # Settings stylesheet contains checkmark icon path for modern UI
        qss_light = get_settings_stylesheet("light")
        self.assertIn("checkmark.png", qss_light)
        self.assertIn("QCheckBox::indicator:checked", qss_light)

        qss_dark = get_settings_stylesheet("dark")
        self.assertIn("checkmark.png", qss_dark)

        # Main window stylesheet also contains modern checkmark
        win_qss = get_window_stylesheet("light")
        self.assertIn("checkmark.png", win_qss)

    def test_quick_convert_silent_already_unicode(self):
        from app.main import BanglaProofreaderApp
        from unittest.mock import patch

        app_inst = BanglaProofreaderApp()
        # Verify on_quick_convert_already_unicode runs without throwing any popup
        with patch("winsound.MessageBeep") as mock_beep:
            app_inst.on_quick_convert_already_unicode()
            mock_beep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
