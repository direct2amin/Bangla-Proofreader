"""Unit tests for System Tray, Windows Autostart Registry, and Font Size Zoom Controller."""

import os
import unittest
from app.core.config import load_config, save_config
from app.core.shortcuts import ShortcutManager
from app.ui.diff_window import DiffWindow
from app.core.engine_manager import EngineManager
from app.utils.autostart import (
    get_app_launch_command,
    is_start_with_windows_enabled,
    set_start_with_windows
)
from app.main import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestTrayAutostartZoom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_autostart_registry(self):
        cmd = get_app_launch_command()
        self.assertIn("--minimized", cmd)

        # Test setting autostart in HKCU Run registry
        res_enable = set_start_with_windows(True)
        self.assertTrue(res_enable)
        self.assertTrue(is_start_with_windows_enabled())

        # Test unsetting autostart
        res_disable = set_start_with_windows(False)
        self.assertTrue(res_disable)
        self.assertFalse(is_start_with_windows_enabled())

    def test_font_size_controller(self):
        engine_mgr = EngineManager()
        window = DiffWindow(engine_manager=engine_mgr)
        window.reset_font_size()

        # Test default font size
        self.assertEqual(window.editor_font_size, 14)

        # Test increase font size
        window.increase_font_size()
        self.assertEqual(window.editor_font_size, 15)
        self.assertEqual(window.orig_edit.font().pointSize(), 15)
        self.assertEqual(window.corr_browser.font().pointSize(), 15)

        # Test decrease font size
        window.decrease_font_size()
        self.assertEqual(window.editor_font_size, 14)

        # Test bounds clamping (min 10, max 22)
        window.apply_font_size(5)
        self.assertEqual(window.editor_font_size, 10)
        window.apply_font_size(30)
        self.assertEqual(window.editor_font_size, 22)

        # Test reset
        window.reset_font_size()
        self.assertEqual(window.editor_font_size, 14)
        self.assertEqual(window.changes_table.font().pointSize(), 14)

        # Test table font size scales
        window.apply_font_size(18)
        self.assertEqual(window.changes_table.font().pointSize(), 18)
        window.reset_font_size()

        # Verify persisted in config
        cfg = load_config()
        self.assertEqual(cfg.get("editor_font_size"), 14)

    def test_shortcut_pause_resume(self):
        mgr = ShortcutManager()
        self.assertFalse(mgr.is_paused)

        mgr.pause()
        self.assertTrue(mgr.is_paused)

        mgr.resume()
        self.assertFalse(mgr.is_paused)

        new_state = mgr.toggle_pause()
        self.assertTrue(new_state)
        self.assertTrue(mgr.is_paused)

    def test_settings_dialog_fields(self):
        from app.ui.settings_dialog import SettingsDialog
        cfg = load_config()

        # English mode
        dlg_en = SettingsDialog(config=cfg, lang="en")
        self.assertTrue(hasattr(dlg_en, "minimize_to_tray_chk"))
        self.assertTrue(hasattr(dlg_en, "start_with_windows_chk"))
        self.assertFalse(hasattr(dlg_en, "auto_paste_chk"))  # Auto-inject option removed!
        self.assertFalse(hasattr(dlg_en, "engine_combo"))  # Mock engine removed completely!
        self.assertFalse(hasattr(dlg_en, "gemini_model_edit"))  # AI Model box removed!
        self.assertTrue(hasattr(dlg_en, "save_key_btn"))  # Save Key button provided!
        self.assertEqual(dlg_en.save_btn.text(), "Save Settings")
        self.assertEqual(dlg_en.cancel_btn.text(), "Cancel")
        self.assertNotIn("(", dlg_en.save_btn.text())  # No mixed language

        # Bengali mode
        dlg_bn = SettingsDialog(config=cfg, lang="bn")
        self.assertEqual(dlg_bn.save_btn.text(), "সংরক্ষণ করুন")
        self.assertEqual(dlg_bn.cancel_btn.text(), "বাতিল")
        self.assertNotIn("(", dlg_bn.save_btn.text())  # No mixed language

        # Verify selectable shortcut combobox options (Z, X, B - and NEVER V, and C is reserved for quick convert)
        self.assertTrue(hasattr(dlg_en, "shortcut_combo"))
        shortcut_values = [dlg_en.shortcut_combo.itemData(i) for i in range(dlg_en.shortcut_combo.count())]
        self.assertEqual(set(shortcut_values), {"ctrl+alt+b", "ctrl+alt+z", "ctrl+alt+x"})
        self.assertNotIn("ctrl+alt+v", shortcut_values)
        self.assertNotIn("ctrl+alt+c", shortcut_values)
        self.assertTrue(hasattr(dlg_en, "quick_convert_chk"))
        self.assertTrue(dlg_en.quick_convert_chk.isChecked())

    def test_win32_shortcut_parser(self):
        from app.core.shortcuts import parse_win32_shortcut, MOD_CONTROL, MOD_ALT
        mods, vk = parse_win32_shortcut("ctrl+alt+b")
        self.assertEqual(mods, MOD_CONTROL | MOD_ALT)
        self.assertEqual(vk, ord("B"))

        mods_z, vk_z = parse_win32_shortcut("ctrl+alt+z")
        self.assertEqual(mods_z, MOD_CONTROL | MOD_ALT)
        self.assertEqual(vk_z, ord("Z"))

    def test_format_gemini_error(self):
        from app.utils.i18n import format_gemini_error
        raw_401 = "Gemini API ত্রুটি: 401 UNAUTHENTICATED. {'error': {'code': 401, 'message': 'Request had invalid authentication credentials.'}}"

        msg_bn = format_gemini_error(raw_401, lang="bn")
        self.assertIn("আপনার এপিআই কী (API Key) টি সঠিক নয়", msg_bn)
        self.assertNotIn("401", msg_bn)
        self.assertNotIn("UNAUTHENTICATED", msg_bn)

        msg_en = format_gemini_error(raw_401, lang="en")
        self.assertIn("Your Gemini API Key is invalid or incorrect", msg_en)
        self.assertNotIn("401", msg_en)

    def test_tray_menu_actions_english(self):
        from app.main import BanglaProofreaderApp
        ctrl = BanglaProofreaderApp()
        if hasattr(ctrl, "restore_action") and ctrl.restore_action:
            self.assertEqual(ctrl.restore_action.text(), "Open / Restore")
            self.assertEqual(ctrl.pause_hotkey_action.text(), "Pause Hotkey")
            ctrl.toggle_hotkey_pause()
            self.assertEqual(ctrl.pause_hotkey_action.text(), "Resume Hotkey")
            ctrl.toggle_hotkey_pause()
            self.assertEqual(ctrl.pause_hotkey_action.text(), "Pause Hotkey")

    def test_quick_convert_worker_offline_conversion(self):
        from unittest.mock import patch
        from app.main import QuickConvertWorker
        from app.core.clipboard import ClipboardManager

        worker = QuickConvertWorker()
        with patch.object(ClipboardManager, "capture_selected_text", return_value="Avwg evsjvq Mvb MvB") as mock_cap, \
             patch.object(ClipboardManager, "paste_into_active_window") as mock_paste:
            worker.run()
            mock_cap.assert_called_once()
            mock_paste.assert_called_once_with("আমি বাংলায় গান গাই", set_clipboard=True)


if __name__ == "__main__":
    unittest.main()
