import os
import webbrowser

try:
    from PyQt6.QtCore import Qt, QUrl, QTimer
    from PyQt6.QtGui import QDesktopServices, QIcon
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
    )
except ImportError:
    from PySide6.QtCore import Qt, QUrl, QTimer
    from PySide6.QtGui import QDesktopServices, QIcon
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
    )

from app.core.clipboard import ClipboardManager
from app.core.theme import get_effective_theme, get_guide_stylesheet, apply_win32_titlebar_theme
from app.core.assets import get_asset_path
from app.utils.i18n import t

AI_STUDIO_URL = "https://aistudio.google.com/app/apikey"
LOGO_ICON_PATH = get_asset_path("logo_icon.png")
LOGO_ICO_PATH = get_asset_path("logo.ico")

DIALOG_STYLESHEET = """
QDialog {
    background-color: #ffffff;
    color: #0f172a;
    font-family: "Nirmala UI";
}
QFrame#HeaderFrame {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 6px;
}
QLabel#DialogTitle {
    font-size: 17px;
    font-weight: bold;
    color: #0b663b;
    background: transparent;
}
QLabel#DialogSubtitle {
    font-size: 13px;
    color: #475569;
    background: transparent;
}
QFrame#StepsFrame {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 14px;
}
QLabel.StepLabel {
    color: #0f172a;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}
QFrame#NoteBanner {
    background-color: #ecfdf5;
    border: 1px solid #a7f3d0;
    border-radius: 6px;
    padding: 8px 12px;
}
QLabel#NoteText {
    color: #065f46;
    font-size: 12.5px;
    font-weight: 500;
    background: transparent;
}
QPushButton#OpenStudioBtn {
    background-color: #0b663b;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 18px;
    border-radius: 6px;
    border: none;
}
QPushButton#OpenStudioBtn:hover {
    background-color: #08502e;
}
QPushButton#CloseBtn {
    background-color: #f1f5f9;
    color: #334155;
    font-weight: 600;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 6px;
    border: 1px solid #cbd5e1;
}
QPushButton#CloseBtn:hover {
    background-color: #e2e8f0;
}
"""


class ApiGuideDialog(QDialog):
    """Modal dialog displaying step-by-step instructions for Gemini API key."""

    def __init__(self, parent=None, lang: str = "en", theme: str = "system"):
        super().__init__(parent)
        self.lang = lang
        self.theme_mode = theme
        self.effective_theme = get_effective_theme(theme)

        # English title on Windows title bar to prevent DWM tofu square rendering
        self.setWindowTitle("How to Get a Free Gemini API Key")
        self.resize(600, 460)
        self.setMinimumSize(540, 420)
        apply_win32_titlebar_theme(self, self.effective_theme)
        self.setStyleSheet(get_guide_stylesheet(self.effective_theme))
        if os.path.exists(LOGO_ICO_PATH):
            self.setWindowIcon(QIcon(LOGO_ICO_PATH))
        elif os.path.exists(LOGO_ICON_PATH):
            self.setWindowIcon(QIcon(LOGO_ICON_PATH))
        self.init_ui()

    @staticmethod
    def open_ai_studio():
        """Open Google AI Studio URL using QDesktopServices with fallback to webbrowser."""
        url = QUrl(AI_STUDIO_URL)
        if not QDesktopServices.openUrl(url):
            webbrowser.open(AI_STUDIO_URL)

    def copy_ai_studio_link(self):
        """Copy the Google AI Studio API Key URL to clipboard without opening browser."""
        ClipboardManager.set_text(AI_STUDIO_URL)
        if hasattr(self, "copy_link_btn") and self.copy_link_btn:
            self.copy_link_btn.setText(t("copy_link_btn_copied", self.lang))
            QTimer.singleShot(
                2200,
                lambda: self.copy_link_btn.setText(t("copy_link_btn", self.lang))
            )

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 6)
        header_layout.setSpacing(4)

        title_lbl = QLabel(t("guide_dialog_title", self.lang))
        title_lbl.setObjectName("DialogTitle")
        header_layout.addWidget(title_lbl)

        subtitle_lbl = QLabel(t("guide_dialog_subtitle", self.lang))
        subtitle_lbl.setObjectName("DialogSubtitle")
        header_layout.addWidget(subtitle_lbl)

        layout.addWidget(header_frame)

        # Steps container
        steps_frame = QFrame()
        steps_frame.setObjectName("StepsFrame")
        steps_layout = QVBoxLayout(steps_frame)
        steps_layout.setSpacing(10)
        steps_layout.setContentsMargins(14, 12, 14, 12)

        # Step 1 with clickable URL (copies link to clipboard) and Copy Link button
        step1_box = QVBoxLayout()
        step1_box.setSpacing(4)

        step1_lbl = QLabel(t("guide_step_1", self.lang))
        step1_lbl.setProperty("class", "StepLabel")
        step1_lbl.setWordWrap(True)
        step1_box.addWidget(step1_lbl)

        url_row = QHBoxLayout()
        url_row.setSpacing(10)

        self.url_btn = QPushButton(f"➜ {AI_STUDIO_URL}")
        url_color = "#34d399" if self.effective_theme == "dark" else "#0b663b"
        self.url_btn.setStyleSheet(
            f"color: {url_color}; text-decoration: underline; background: transparent; border: none; "
            "text-align: left; font-weight: 600; font-size: 13px; padding: 2px 0;"
        )
        self.url_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.url_btn.setToolTip(t("copy_link_btn", self.lang))
        self.url_btn.clicked.connect(self.copy_ai_studio_link)
        url_row.addWidget(self.url_btn)

        self.copy_link_btn = QPushButton(t("copy_link_btn", self.lang))
        copy_bg = "#334155" if self.effective_theme == "dark" else "#e2e8f0"
        copy_fg = "#f8fafc" if self.effective_theme == "dark" else "#0f172a"
        copy_border = "#475569" if self.effective_theme == "dark" else "#cbd5e1"
        self.copy_link_btn.setStyleSheet(
            f"background-color: {copy_bg}; color: {copy_fg}; border: 1px solid {copy_border}; "
            "border-radius: 5px; font-weight: 600; font-size: 12px; padding: 3px 10px;"
        )
        self.copy_link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_link_btn.clicked.connect(self.copy_ai_studio_link)
        url_row.addWidget(self.copy_link_btn)
        url_row.addStretch()

        step1_box.addLayout(url_row)

        steps_layout.addLayout(step1_box)

        # Steps 2 to 5
        for step_key in ("guide_step_2", "guide_step_3", "guide_step_4", "guide_step_5"):
            step_lbl = QLabel(t(step_key, self.lang))
            step_lbl.setProperty("class", "StepLabel")
            step_lbl.setWordWrap(True)
            steps_layout.addWidget(step_lbl)

        layout.addWidget(steps_frame)

        # Note banner
        note_frame = QFrame()
        note_frame.setObjectName("NoteBanner")
        note_layout = QHBoxLayout(note_frame)
        note_layout.setContentsMargins(10, 8, 10, 8)

        note_lbl = QLabel(t("guide_note", self.lang))
        note_lbl.setObjectName("NoteText")
        note_lbl.setWordWrap(True)
        note_layout.addWidget(note_lbl)

        layout.addWidget(note_frame)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()
        open_web_btn = QPushButton(t("open_aistudio_btn", self.lang))
        open_web_btn.setObjectName("OpenStudioBtn")
        open_web_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_web_btn.clicked.connect(self.open_ai_studio)
        btn_layout.addWidget(open_web_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(t("close_btn", self.lang))
        close_btn.setObjectName("CloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
