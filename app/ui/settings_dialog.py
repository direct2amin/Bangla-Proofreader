"""Settings dialog for Gemini API configuration, shortcuts, autostart, and system tray behavior."""

from __future__ import annotations

import os

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QGroupBox, QFormLayout, QCheckBox, QMessageBox,
        QComboBox
    )
except ImportError:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QGroupBox, QFormLayout, QCheckBox, QMessageBox,
        QComboBox
    )

from app.core.config import load_config, save_config
from app.core.theme import (
    get_effective_theme,
    get_settings_stylesheet,
    apply_win32_titlebar_theme,
    show_themed_message_box,
)
from app.core.assets import get_asset_path
from app.utils.autostart import is_start_with_windows_enabled, set_start_with_windows
from app.utils.i18n import t

LOGO_ICON_PATH = get_asset_path("logo_icon.png")
LOGO_ICO_PATH = get_asset_path("logo.ico")

SETTINGS_STYLESHEET = """
QDialog {
    background-color: #ffffff;
    color: #0f172a;
    font-family: "Nirmala UI";
}

QGroupBox {
    font-weight: bold;
    font-size: 13px;
    color: #0b663b;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    padding-left: 14px;
    padding-right: 14px;
    padding-bottom: 14px;
    background-color: #f8fafc;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: #0b663b;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    font-weight: 600;
}

QLabel {
    color: #334155;
    font-size: 13px;
    font-weight: 500;
}

QLineEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1.5px solid #0b663b;
}

QCheckBox {
    color: #1e293b;
    font-size: 13px;
    spacing: 8px;
}

QPushButton {
    font-size: 13px;
    font-weight: 600;
    padding: 8px 20px;
    border-radius: 6px;
    font-family: "Nirmala UI";
}

QPushButton#SaveKeyBtn {
    background-color: #0b663b;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 7px 16px;
    border-radius: 6px;
    border: none;
}

QPushButton#SaveKeyBtn:hover {
    background-color: #08502e;
}

QPushButton#SaveBtn {
    background-color: #0b663b;
    color: #ffffff;
    border: none;
}

QPushButton#SaveBtn:hover {
    background-color: #08502e;
}

QPushButton#CancelBtn {
    background-color: #ffffff;
    color: #475569;
    border: 1px solid #cbd5e1;
}

QPushButton#CancelBtn:hover {
    background-color: #f1f5f9;
}
"""


class SettingsDialog(QDialog):
    """Configuration dialog for Bangla Proofreader."""

    def __init__(self, parent=None, config=None, lang: str = "en", theme: str = "system"):
        super().__init__(parent)
        self.config = config or {}
        self.lang = lang
        self.theme_mode = self.config.get("theme", theme)
        self.effective_theme = get_effective_theme(self.theme_mode)

        # Keep title in English on Windows title bar to prevent tofu squares
        self.setWindowTitle("Settings - Bangla Proofreader")
        self.resize(520, 460)
        apply_win32_titlebar_theme(self, self.effective_theme)
        self.setStyleSheet(get_settings_stylesheet(self.effective_theme))

        if os.path.exists(LOGO_ICO_PATH):
            self.setWindowIcon(QIcon(LOGO_ICO_PATH))
        elif os.path.exists(LOGO_ICON_PATH):
            self.setWindowIcon(QIcon(LOGO_ICON_PATH))

        self.init_ui()

    def on_theme_changed(self):
        """Dynamically update dialog style when theme is changed in combobox."""
        selected_theme = self.theme_combo.currentData()
        eff = get_effective_theme(selected_theme)
        self.effective_theme = eff
        apply_win32_titlebar_theme(self, eff)
        self.setStyleSheet(get_settings_stylesheet(eff))

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        # 1. Appearance & Theme Group (Light, Dark, System Default)
        theme_group = QGroupBox(t("settings_theme_group", self.lang))
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(10)

        theme_row = QHBoxLayout()
        theme_lbl = QLabel(t("settings_theme_label", self.lang))
        theme_lbl.setFixedWidth(70)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t("theme_light", self.lang), "light")
        self.theme_combo.addItem(t("theme_dark", self.lang), "dark")
        self.theme_combo.addItem(t("theme_system", self.lang), "system")

        current_theme = self.config.get("theme", "system")
        idx = self.theme_combo.findData(current_theme)
        if idx != -1:
            self.theme_combo.setCurrentIndex(idx)
        else:
            self.theme_combo.setCurrentIndex(2)

        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.theme_combo)
        theme_layout.addLayout(theme_row)
        layout.addWidget(theme_group)

        # 2. Gemini API Settings Group (AI Model box removed, Save Key provided)
        gemini_group = QGroupBox(t("settings_api_group", self.lang))
        gemini_layout = QVBoxLayout(gemini_group)
        gemini_layout.setSpacing(10)

        key_row = QHBoxLayout()
        key_lbl = QLabel(t("settings_api_key_label", self.lang))
        key_lbl.setFixedWidth(70)

        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_edit.setPlaceholderText(t("settings_api_key_placeholder", self.lang))
        self.gemini_key_edit.setText(self.config.get("gemini_api_key", ""))

        self.save_key_btn = QPushButton(t("save_key", self.lang))
        self.save_key_btn.setObjectName("SaveKeyBtn")
        self.save_key_btn.clicked.connect(self.save_api_key_directly)

        key_row.addWidget(key_lbl)
        key_row.addWidget(self.gemini_key_edit)
        key_row.addWidget(self.save_key_btn)

        gemini_layout.addLayout(key_row)
        layout.addWidget(gemini_group)

        # 2. Shortcuts, System Tray & Windows Autostart Group
        behavior_group = QGroupBox(t("settings_behavior_group", self.lang))
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setSpacing(10)

        sc_row = QHBoxLayout()
        sc_lbl = QLabel(t("settings_shortcut_label", self.lang))
        self.shortcut_combo = QComboBox()
        for label, value in (
            ("Ctrl+Alt+B", "ctrl+alt+b"),
            ("Ctrl+Alt+Z", "ctrl+alt+z"),
            ("Ctrl+Alt+X", "ctrl+alt+x"),
        ):
            self.shortcut_combo.addItem(label, value)

        current_sc = (self.config.get("shortcut", "ctrl+alt+b") or "ctrl+alt+b").strip().lower()
        if current_sc not in ("ctrl+alt+b", "ctrl+alt+z", "ctrl+alt+x"):
            current_sc = "ctrl+alt+b"
        sc_idx = self.shortcut_combo.findData(current_sc)
        if sc_idx != -1:
            self.shortcut_combo.setCurrentIndex(sc_idx)
        else:
            self.shortcut_combo.setCurrentIndex(0)

        sc_row.addWidget(sc_lbl)
        sc_row.addWidget(self.shortcut_combo)
        behavior_layout.addLayout(sc_row)

        self.quick_convert_chk = QCheckBox(t("settings_quick_convert", self.lang))
        self.quick_convert_chk.setChecked(self.config.get("quick_convert_enabled", True))
        self.quick_convert_chk.setToolTip(t("settings_quick_convert_tip", self.lang))
        behavior_layout.addWidget(self.quick_convert_chk)

        self.minimize_to_tray_chk = QCheckBox(t("settings_minimize_tray", self.lang))
        self.minimize_to_tray_chk.setChecked(self.config.get("minimize_to_tray_on_close", True))
        behavior_layout.addWidget(self.minimize_to_tray_chk)

        self.start_with_windows_chk = QCheckBox(t("settings_start_windows", self.lang))
        autostart_active = is_start_with_windows_enabled() or self.config.get("start_with_windows", False)
        self.start_with_windows_chk.setChecked(autostart_active)
        behavior_layout.addWidget(self.start_with_windows_chk)

        layout.addWidget(behavior_group)

        # 3. Dialog Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_btn = QPushButton(t("settings_save_btn", self.lang))
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton(t("settings_cancel_btn", self.lang))
        self.cancel_btn.setObjectName("CancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def save_api_key_directly(self):
        """Save the entered API key directly with confirmation."""
        key = self.gemini_key_edit.text().strip()
        msg = t("confirm_save_key_msg", self.lang) if key else t("confirm_clear_key_msg", self.lang)
        reply = show_themed_message_box(
            self,
            "question",
            t("confirm_save_key_title", self.lang),
            msg,
            effective_theme=self.effective_theme,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config["gemini_api_key"] = key
            cfg = load_config()
            cfg["gemini_api_key"] = key
            save_config(cfg)
            show_themed_message_box(
                self,
                "information",
                t("confirm_save_key_title", self.lang),
                t("api_saved" if key else "api_cleared", self.lang),
                effective_theme=self.effective_theme,
            )

    def save_settings(self):
        """Save settings and apply Windows registry autostart."""
        self.config["theme"] = self.theme_combo.currentData()
        self.config["engine"] = "gemini"
        self.config["gemini_api_key"] = self.gemini_key_edit.text().strip()
        sc = self.shortcut_combo.currentData()
        if sc not in ("ctrl+alt+b", "ctrl+alt+z", "ctrl+alt+x"):
            sc = "ctrl+alt+b"
        self.config["shortcut"] = sc
        self.config["quick_convert_enabled"] = self.quick_convert_chk.isChecked()
        self.config["minimize_to_tray_on_close"] = self.minimize_to_tray_chk.isChecked()

        start_with_win = self.start_with_windows_chk.isChecked()
        self.config["start_with_windows"] = start_with_win
        set_start_with_windows(start_with_win)

        self.accept()
