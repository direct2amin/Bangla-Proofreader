"""Unit tests for Dark Mode, Light Mode, and System Theme functionality."""

import os
import unittest

from app.core.theme import (
    get_system_theme,
    get_effective_theme,
    get_window_stylesheet,
    get_settings_stylesheet,
    get_about_stylesheet,
    get_guide_stylesheet,
    get_diff_spans
)
from app.utils.diff_highlighter import DiffHighlighter
from app.ui.settings_dialog import SettingsDialog
from app.ui.diff_window import DiffWindow
from app.core.engine_manager import EngineManager
from app.main import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestTheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_theme_resolution(self):
        """Verify theme mode resolution."""
        self.assertEqual(get_effective_theme("light"), "light")
        self.assertEqual(get_effective_theme("dark"), "dark")

        # 'system' mode resolves to either 'light' or 'dark' matching OS
        sys_theme = get_system_theme()
        self.assertIn(sys_theme, ["light", "dark"])
        self.assertEqual(get_effective_theme("system"), sys_theme)

    def test_stylesheet_generation(self):
        """Verify dark and light stylesheets contain appropriate palette rules."""
        dark_win = get_window_stylesheet("dark")
        self.assertIn("#0f172a", dark_win)
        self.assertIn("#1e293b", dark_win)

        light_win = get_window_stylesheet("light")
        self.assertIn("#ffffff", light_win)
        self.assertIn("#f8fafc", light_win)

        dark_settings = get_settings_stylesheet("dark")
        self.assertIn("#0f172a", dark_settings)

        light_settings = get_settings_stylesheet("light")
        self.assertIn("#ffffff", light_settings)

        dark_about = get_about_stylesheet("dark")
        self.assertIn("#0f172a", dark_about)

        dark_guide = get_guide_stylesheet("dark")
        self.assertIn("#0f172a", dark_guide)

    def test_diff_spans_contrast(self):
        """Verify diff markup styles adapt to dark/light theme."""
        light_spans = get_diff_spans(is_dark=False)
        self.assertIn("#fee2e2", light_spans["del_style"])
        self.assertIn("#dcfce7", light_spans["ins_style"])

        dark_spans = get_diff_spans(is_dark=True)
        self.assertIn("#450a0a", dark_spans["del_style"])
        self.assertIn("#064e3b", dark_spans["ins_style"])

    def test_diff_highlighter_with_theme(self):
        """Verify DiffHighlighter injects theme-appropriate CSS spans."""
        orig = "ভুল বানান"
        corr = "শুদ্ধ বানান"

        res_light = DiffHighlighter.compute_diff(orig, corr, is_dark=False)
        self.assertIn("#fee2e2", res_light.inline_html)
        self.assertIn("#dcfce7", res_light.inline_html)

        res_dark = DiffHighlighter.compute_diff(orig, corr, is_dark=True)
        self.assertIn("#450a0a", res_dark.inline_html)
        self.assertIn("#064e3b", res_dark.inline_html)

    def test_settings_dialog_theme_combo(self):
        """Verify SettingsDialog has 3 theme options and updates config."""
        cfg = {"theme": "light"}
        dlg = SettingsDialog(config=cfg, lang="en")

        self.assertEqual(dlg.theme_combo.count(), 3)
        self.assertEqual(dlg.theme_combo.itemData(0), "light")
        self.assertEqual(dlg.theme_combo.itemData(1), "dark")
        self.assertEqual(dlg.theme_combo.itemData(2), "system")

        # Initial selection matches config
        self.assertEqual(dlg.theme_combo.currentData(), "light")

        # Switch to dark
        dlg.theme_combo.setCurrentIndex(1)
        self.assertEqual(dlg.theme_combo.currentData(), "dark")

        # Save settings and verify persistence in config
        dlg.save_settings()
        self.assertEqual(dlg.config["theme"], "dark")

    def test_diff_window_apply_theme(self):
        """Verify DiffWindow dynamically applies theme."""
        engine_mgr = EngineManager()
        window = DiffWindow(engine_manager=engine_mgr)

        window.apply_theme("dark")
        self.assertEqual(window.theme_mode, "dark")
        self.assertEqual(window.effective_theme, "dark")
        self.assertIn("#0f172a", window.styleSheet())

        window.apply_theme("light")
        self.assertEqual(window.theme_mode, "light")
        self.assertEqual(window.effective_theme, "light")
        self.assertIn("#ffffff", window.styleSheet())
        self.assertIn("QMessageBox", window.styleSheet())

        from app.core.theme import get_messagebox_stylesheet
        light_mb = get_messagebox_stylesheet("light")
        dark_mb = get_messagebox_stylesheet("dark")
        self.assertIn("background-color: #ffffff", light_mb)
        self.assertIn("color: #0f172a", light_mb)
        self.assertIn("background-color: #1e293b", dark_mb)
        self.assertIn("color: #f8fafc", dark_mb)


if __name__ == "__main__":
    unittest.main()
