"""Diff review window for Bangla Proofreader with language switching and threaded worker."""

from __future__ import annotations

import html
import logging
import os
from typing import Optional, Set

try:
    from PyQt6.QtCore import Qt, Signal, Slot, QTimer, QThread, QEvent
    from PyQt6.QtGui import (
        QFont, QIcon, QColor, QPixmap, QTextCursor, QTextBlockFormat, QTextCharFormat, QBrush
    )
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
        QTextEdit, QTextBrowser, QLabel, QPushButton,
        QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
        QFrame, QStatusBar, QMessageBox, QApplication, QLineEdit,
        QCheckBox, QProgressBar, QComboBox
    )
except ImportError:
    from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QEvent
    from PySide6.QtGui import (
        QFont, QIcon, QColor, QPixmap, QTextCursor, QTextBlockFormat, QTextCharFormat, QBrush
    )
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
        QTextEdit, QTextBrowser, QLabel, QPushButton,
        QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
        QFrame, QStatusBar, QMessageBox, QApplication, QLineEdit,
        QCheckBox, QProgressBar, QComboBox
    )

from app.utils.diff_highlighter import DiffHighlighter, DiffResult, is_word
from app.engines.sentence_polisher import SentencePolishResult, SentenceChange
from app.utils.i18n import t, format_gemini_error
from app.core.engine_manager import EngineManager
from app.core.clipboard import ClipboardManager
from app.core.config import load_config, save_config
from app.ui.api_guide_dialog import ApiGuideDialog
from app.ui.about_dialog import AboutDialog
from app.ui.settings_dialog import SettingsDialog
from app.utils.foreign_words import is_foreign_word, is_arabic_word, get_word_classification
from app.utils.punctuation_formatter import format_bangla_punctuation
from app.utils.bijoy_converter import is_bijoy_text, convert_bijoy_to_unicode

from app.core.theme import (
    get_effective_theme,
    get_window_stylesheet,
    apply_win32_titlebar_theme,
    show_themed_message_box,
)
from app.core.assets import get_asset_path

logger = logging.getLogger(__name__)

UI_FONT_FAMILY = "Nirmala UI"
TEXT_FIELD_FONT_FAMILY = "Bornomala Trio"
BANGLA_FONT = "Nirmala UI"
LOGO_BANNER_PATH = get_asset_path("logo_banner.png")
LOGO_ICON_PATH = get_asset_path("logo_icon.png")
LOGO_ICO_PATH = get_asset_path("logo.ico")

WINDOW_STYLESHEET = get_window_stylesheet("light", BANGLA_FONT)


def create_ui_font(size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Create QFont for System UI controls using native Windows Segoe UI / Nirmala UI."""
    f = QFont()
    f.setFamilies([UI_FONT_FAMILY, "Segoe UI", "sans-serif"])
    f.setPointSize(size)
    f.setWeight(weight)
    return f


def create_editor_font(size: int = 14) -> QFont:
    """Create dedicated QFont for Text Fields (Input, Output, Diff) using Bornomala Trio (Bangla, Arabic, English)."""
    f = QFont()
    f.setFamilies([TEXT_FIELD_FONT_FAMILY, UI_FONT_FAMILY, "Segoe UI", "sans-serif"])
    f.setPointSize(size)
    return f


def create_bangla_font(size: int = 14) -> QFont:
    """Compatibility alias pointing to create_editor_font."""
    return create_editor_font(size)


class ProofreadWorker(QThread):
    """Background worker thread to execute Gemini API proofreading asynchronously without UI freeze."""

    progress_signal = Signal(str)
    finished_signal = Signal(str, object)  # corrected_text, diff_result
    error_signal = Signal(str)

    def __init__(self, engine_manager: EngineManager, text: str, lang: str, is_dark: bool = False):
        super().__init__()
        self.engine_manager = engine_manager
        self.text = text
        self.lang = lang
        self.is_dark = is_dark

    def run(self):
        try:
            self.progress_signal.emit(t("progress_sending", self.lang))
            corrected_text = self.engine_manager.proofread(self.text)

            self.progress_signal.emit(t("progress_analyzing", self.lang))
            diff_result = DiffHighlighter.compute_diff(self.text, corrected_text, is_dark=self.is_dark)

            self.progress_signal.emit(t("progress_done", self.lang))
            self.finished_signal.emit(corrected_text, diff_result)
        except Exception as e:
            logger.error("ProofreadWorker error: %s", e)
            self.error_signal.emit(str(e))


class PolishWorker(QThread):
    """Background worker thread to execute Sentence Polish asynchronously without UI freeze."""

    progress_signal = Signal(str)
    finished_signal = Signal(object)  # SentencePolishResult
    error_signal = Signal(str)

    def __init__(self, engine_manager: EngineManager, text: str, lang: str):
        super().__init__()
        self.engine_manager = engine_manager
        self.text = text
        self.lang = lang

    def run(self):
        try:
            self.progress_signal.emit(t("progress_polishing", self.lang))
            polish_result = self.engine_manager.polish_sentences(self.text)
            self.finished_signal.emit(polish_result)
        except Exception as e:
            logger.error("PolishWorker error: %s", e)
            self.error_signal.emit(str(e))


class DiffWindow(QMainWindow):
    """Main Review & Diff Window with language toggle, threading, and selective changes."""

    replace_requested = Signal(str)
    shortcut_changed = Signal(str)

    def __init__(self, engine_manager: Optional[EngineManager] = None):
        super().__init__()
        self.engine_manager = engine_manager or EngineManager()
        self.last_diff_result: Optional[DiffResult] = None
        self.accepted_change_ids: Set[int] = set()
        self.worker: Optional[ProofreadWorker] = None
        self.spelling_checked: bool = False
        self.polish_worker: Optional[PolishWorker] = None
        self.last_polish_result: Optional[SentencePolishResult] = None
        self.accepted_sentence_ids: Set[int] = set()

        # Load configuration (Default language: English, Default theme: system)
        config = load_config()
        self.lang = config.get("ui_language", "en")
        self.editor_font_size = int(config.get("editor_font_size", 14))
        self.theme_mode = config.get("theme", "system")
        self.effective_theme = get_effective_theme(self.theme_mode)

        # English window title (no tofu boxes on Windows title bar)
        self.setWindowTitle("Bangla Proofreader")
        self.resize(1060, 720)
        self.setMinimumSize(820, 540)
        self.setStyleSheet(get_window_stylesheet(self.effective_theme, BANGLA_FONT))

        if os.path.exists(LOGO_ICO_PATH):
            self.setWindowIcon(QIcon(LOGO_ICO_PATH))
        elif os.path.exists(LOGO_ICON_PATH):
            self.setWindowIcon(QIcon(LOGO_ICON_PATH))

        self.init_ui()
        self.apply_theme(self.theme_mode)
        self.apply_language()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. Header Bar
        header_frame = QFrame()
        header_frame.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        if os.path.exists(LOGO_BANNER_PATH):
            self.logo_lbl = QLabel()
            banner_pix = QPixmap(LOGO_BANNER_PATH).scaledToHeight(50, Qt.TransformationMode.SmoothTransformation)
            self.logo_lbl.setPixmap(banner_pix)
            title_col.addWidget(self.logo_lbl)
            self.title_lbl = None
        else:
            self.title_lbl = QLabel(t("app_title", self.lang))
            self.title_lbl.setObjectName("AppTitle")
            title_col.addWidget(self.title_lbl)
            self.logo_lbl = None

        self.subtitle_lbl = QLabel(t("app_subtitle", self.lang))
        self.subtitle_lbl.setObjectName("AppSubtitle")
        title_col.addWidget(self.subtitle_lbl)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        # Language Switcher & API Key Box
        config = load_config()
        header_controls = QVBoxLayout()

        top_controls_row = QHBoxLayout()
        top_controls_row.setSpacing(8)
        top_controls_row.addStretch()

        # Language Toggle Button
        self.lang_btn = QPushButton()
        self.lang_btn.setObjectName("LangBtn")
        self.lang_btn.setToolTip("Switch Language / ভাষা পরিবর্তন করুন")
        self.lang_btn.clicked.connect(self.toggle_language)
        top_controls_row.addWidget(self.lang_btn)

        # API Guide Button
        self.guide_btn = QPushButton()
        self.guide_btn.clicked.connect(self.open_api_guide)
        top_controls_row.addWidget(self.guide_btn)

        # Settings Dialog Button
        self.settings_btn = QPushButton()
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        top_controls_row.addWidget(self.settings_btn)

        # About Dialog Button
        self.about_btn = QPushButton()
        self.about_btn.clicked.connect(self.open_about_dialog)
        top_controls_row.addWidget(self.about_btn)

        header_controls.addLayout(top_controls_row)

        api_row = QHBoxLayout()
        self.api_lbl = QLabel()
        self.api_lbl.setStyleSheet("font-weight: 600; color: #475569;")

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter Gemini API Key...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(config.get("gemini_api_key", ""))
        self.api_key_input.setFixedWidth(240)

        self.save_key_btn = QPushButton()
        self.save_key_btn.setObjectName("SaveKeyBtn")
        self.save_key_btn.clicked.connect(self.save_api_key)

        api_row.addWidget(self.api_lbl)
        api_row.addWidget(self.api_key_input)
        api_row.addWidget(self.save_key_btn)
        header_controls.addLayout(api_row)

        header_layout.addLayout(header_controls)
        main_layout.addWidget(header_frame)

        # Status Notification Banner
        self.status_banner = QLabel("")
        self.status_banner.setStyleSheet(
            "border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 500;"
        )
        main_layout.addWidget(self.status_banner)

        # 2. Controls Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        self.paste_btn = QPushButton()
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        toolbar_layout.addWidget(self.paste_btn)

        self.proofread_btn = QPushButton()
        self.proofread_btn.setObjectName("PrimaryBtn")
        self.proofread_btn.clicked.connect(self.run_proofread)
        toolbar_layout.addWidget(self.proofread_btn)

        self.polish_btn = QPushButton()
        self.polish_btn.setObjectName("SecondaryBtn")
        self.polish_btn.clicked.connect(self.run_sentence_polish)
        toolbar_layout.addWidget(self.polish_btn)

        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self.clear_all)
        toolbar_layout.addWidget(self.clear_btn)

        toolbar_layout.addStretch()

        # Font size zoom controls (A- / Reset / A+)
        zoom_frame = QFrame()
        zoom_frame.setObjectName("ZoomFrame")
        zoom_frame.setMinimumWidth(185)
        zoom_layout = QHBoxLayout(zoom_frame)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(4)

        self.zoom_lbl = QLabel(t("zoom_label", self.lang))
        self.zoom_lbl.setStyleSheet("font-weight: 600; color: #475569; font-size: 13px;")
        zoom_layout.addWidget(self.zoom_lbl)

        self.zoom_out_btn = QPushButton("A-")
        self.zoom_out_btn.setToolTip("Decrease Font Size (ফন্ট ছোট করুন)")
        self.zoom_out_btn.setFixedWidth(36)
        self.zoom_out_btn.clicked.connect(self.decrease_font_size)
        zoom_layout.addWidget(self.zoom_out_btn)

        self.zoom_reset_btn = QPushButton(f"{self.editor_font_size}pt")
        self.zoom_reset_btn.setToolTip("Reset Font Size to 14pt (ডিফল্ট রিসেট)")
        self.zoom_reset_btn.setFixedWidth(58)
        self.zoom_reset_btn.clicked.connect(self.reset_font_size)
        zoom_layout.addWidget(self.zoom_reset_btn)

        self.zoom_in_btn = QPushButton("A+")
        self.zoom_in_btn.setToolTip("Increase Font Size (ফন্ট বড় করুন)")
        self.zoom_in_btn.setFixedWidth(36)
        self.zoom_in_btn.clicked.connect(self.increase_font_size)
        zoom_layout.addWidget(self.zoom_in_btn)

        toolbar_layout.addWidget(zoom_frame)
        main_layout.addLayout(toolbar_layout)

        # 3. Main Diff & Review Tabs
        self.tabs = QTabWidget()

        # --- Tab 1: Side by Side Review ---
        sbs_widget = QWidget()
        sbs_layout = QVBoxLayout(sbs_widget)
        sbs_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Original text
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.orig_header = QLabel()
        self.orig_header.setStyleSheet("font-weight: bold; color: #dc2626;")
        self.orig_edit = QTextEdit()
        self.orig_edit.setAcceptRichText(False)
        self.orig_edit.setPlaceholderText("Paste or type Bangla text here...")
        self.orig_edit.textChanged.connect(self.on_input_text_changed)
        left_layout.addWidget(self.orig_header)
        left_layout.addWidget(self.orig_edit)

        # Right: Corrected text
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.corr_header = QLabel()
        self.corr_header.setStyleSheet("font-weight: bold; color: #16a34a;")
        self.corr_browser = QTextBrowser()
        self.corr_browser.setOpenExternalLinks(False)
        right_layout.addWidget(self.corr_header)
        right_layout.addWidget(self.corr_browser)

        # Standardize typography & margins for side-by-side alignment
        bangla_font = create_bangla_font(self.editor_font_size)
        self.orig_edit.setFont(bangla_font)
        self.corr_browser.setFont(bangla_font)
        self.orig_edit.document().setDocumentMargin(8)
        self.corr_browser.document().setDocumentMargin(8)
        self._apply_uniform_line_spacing(self.orig_edit)
        self._apply_uniform_line_spacing(self.corr_browser)

        # Synchronize vertical scrolling between left and right editors
        self._syncing_scroll = False
        def sync_orig_to_corr(val):
            if not self._syncing_scroll:
                self._syncing_scroll = True
                self.corr_browser.verticalScrollBar().setValue(val)
                self._syncing_scroll = False

        def sync_corr_to_orig(val):
            if not self._syncing_scroll:
                self._syncing_scroll = True
                self.orig_edit.verticalScrollBar().setValue(val)
                self._syncing_scroll = False

        self.orig_edit.verticalScrollBar().valueChanged.connect(sync_orig_to_corr)
        self.corr_browser.verticalScrollBar().valueChanged.connect(sync_corr_to_orig)

        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 520])
        sbs_layout.addWidget(splitter)
        self.tabs.addTab(sbs_widget, "")

        # --- Tab 2: Inline Diff View ---
        inline_widget = QWidget()
        inline_layout = QVBoxLayout(inline_widget)
        inline_layout.setContentsMargins(8, 8, 8, 8)
        self.inline_header = QLabel()
        self.inline_header.setStyleSheet("font-weight: bold; color: #334155;")
        self.inline_browser = QTextBrowser()
        self.inline_browser.setFont(bangla_font)
        self.inline_browser.document().setDocumentMargin(8)
        self._apply_uniform_line_spacing(self.inline_browser)
        inline_layout.addWidget(self.inline_header)
        inline_layout.addWidget(self.inline_browser)
        self.tabs.addTab(inline_widget, "")

        # --- Tab 3: Detailed Changes List with Accept/Reject checkboxes ---
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(8)

        # Table Control Buttons
        table_controls = QHBoxLayout()
        self.table_instruction = QLabel()
        self.table_instruction.setStyleSheet("font-weight: 600; color: #475569;")
        table_controls.addWidget(self.table_instruction)

        table_controls.addStretch()

        self.accept_all_btn = QPushButton()
        self.accept_all_btn.clicked.connect(self.accept_all_changes)
        table_controls.addWidget(self.accept_all_btn)

        self.reject_all_btn = QPushButton()
        self.reject_all_btn.clicked.connect(self.reject_all_changes)
        table_controls.addWidget(self.reject_all_btn)

        self.exclude_foreign_btn = QPushButton()
        self.exclude_foreign_btn.clicked.connect(self.exclude_foreign_words)
        table_controls.addWidget(self.exclude_foreign_btn)

        table_layout.addLayout(table_controls)

        # Changes Table
        self.changes_table = QTableWidget(0, 4)
        self.changes_table.setFont(bangla_font)
        self.changes_table.horizontalHeader().setFont(create_bangla_font(max(10, self.editor_font_size - 1)))
        self.changes_table.verticalHeader().setDefaultSectionSize(max(30, int(self.editor_font_size * 2.3)))
        self.changes_table.setWordWrap(True)
        self.changes_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        c_hdr = self.changes_table.horizontalHeader()
        c_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.changes_table.setColumnWidth(0, 55)
        c_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.changes_table.setColumnWidth(1, 160)
        c_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.changes_table.setColumnWidth(2, 160)
        c_hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.changes_table.setColumnWidth(3, 140)
        c_hdr.setStretchLastSection(True)
        table_layout.addWidget(self.changes_table)

        self.tabs.addTab(table_widget, "")

        # Dedicated Sentence Polish View Tab
        sentence_widget = QWidget()
        sentence_layout = QVBoxLayout(sentence_widget)
        sentence_layout.setContentsMargins(4, 4, 4, 4)

        sentence_controls = QHBoxLayout()
        self.sentence_instruction = QLabel()
        self.sentence_instruction.setStyleSheet("font-weight: 600; color: #475569;")
        sentence_controls.addWidget(self.sentence_instruction)

        sentence_controls.addStretch()

        self.accept_all_sentences_btn = QPushButton()
        self.accept_all_sentences_btn.clicked.connect(self.accept_all_sentences)
        sentence_controls.addWidget(self.accept_all_sentences_btn)

        self.reject_all_sentences_btn = QPushButton()
        self.reject_all_sentences_btn.clicked.connect(self.reject_all_sentences)
        sentence_controls.addWidget(self.reject_all_sentences_btn)

        sentence_layout.addLayout(sentence_controls)

        self.sentence_table = QTableWidget(0, 4)
        self.sentence_table.setFont(bangla_font)
        self.sentence_table.horizontalHeader().setFont(create_bangla_font(max(10, self.editor_font_size - 1)))
        self.sentence_table.setWordWrap(True)
        self.sentence_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.sentence_table.verticalHeader().setDefaultSectionSize(max(42, int(self.editor_font_size * 2.8)))
        
        s_hdr = self.sentence_table.horizontalHeader()
        s_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.sentence_table.setColumnWidth(0, 55)
        s_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.sentence_table.setColumnWidth(1, 280)
        s_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.sentence_table.setColumnWidth(2, 280)
        s_hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.sentence_table.setColumnWidth(3, 240)
        s_hdr.setStretchLastSection(True)
        sentence_layout.addWidget(self.sentence_table)

        self.tabs.addTab(sentence_widget, "")
        main_layout.addWidget(self.tabs, stretch=1)

        # 4. Bottom Action Bar & Status
        bottom_layout = QHBoxLayout()

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #475569; font-weight: 600;")
        bottom_layout.addWidget(self.stats_label)

        bottom_layout.addStretch()

        self.feedback_label = QLabel("")
        self.feedback_label.setStyleSheet("color: #16a34a; font-weight: 600; padding-right: 10px;")
        bottom_layout.addWidget(self.feedback_label)

        self.copy_btn = QPushButton()
        self.copy_btn.clicked.connect(self.copy_corrected_text)
        bottom_layout.addWidget(self.copy_btn)

        self.replace_btn = QPushButton()
        self.replace_btn.setObjectName("SuccessBtn")
        self.replace_btn.clicked.connect(self.replace_in_active_app)
        bottom_layout.addWidget(self.replace_btn)

        main_layout.addLayout(bottom_layout)

        # Status Bar (Bottom-left permanently displays the active Global Shortcut from Settings)
        self.status_bar = QStatusBar()
        self.shortcut_status_label = QLabel()
        self.shortcut_status_label.setContentsMargins(6, 2, 6, 2)
        self.status_bar.addWidget(self.shortcut_status_label)

        # Progress bar and status log placed in status bar next to Global Shortcut
        self.status_bar_separator = QLabel("  |  ")
        self.status_bar_separator.setStyleSheet("color: #94a3b8; font-weight: 400;")
        self.status_bar_separator.setVisible(False)
        self.status_bar.addWidget(self.status_bar_separator)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate animation
        self.progress_bar.setFixedWidth(130)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)

        self.progress_log_lbl = QLabel("")
        self.progress_log_lbl.setStyleSheet("color: #2563eb; font-weight: 600; font-size: 12px; margin-left: 6px;")
        self.progress_log_lbl.setVisible(False)
        self.status_bar.addWidget(self.progress_log_lbl)

        self.setStatusBar(self.status_bar)

    def update_shortcut_status(self, shortcut: Optional[str] = None) -> None:
        """Update bottom-left status label with the currently configured Global Shortcut."""
        if shortcut:
            self._active_shortcut = shortcut.strip().lower()
        raw_sc = (
            getattr(self, "_active_shortcut", None)
            or load_config().get("shortcut", "ctrl+alt+b")
            or "ctrl+alt+b"
        ).strip().lower()
        if raw_sc not in ("ctrl+alt+b", "ctrl+alt+z", "ctrl+alt+x"):
            raw_sc = "ctrl+alt+b"
        sc_display = "+".join(part.capitalize() for part in raw_sc.split("+"))
        status_text = t("status_shortcut", self.lang).replace("Ctrl+Alt+B", sc_display)
        self.status_bar.clearMessage()
        self.shortcut_status_label.setText(status_text)

    def apply_language(self):
        """Update all UI elements to the active language (pure English or pure Bangla)."""
        lang = self.lang
        self.setWindowTitle("Bangla Proofreader")
        if self.title_lbl:
            self.title_lbl.setText(t("app_title", lang))
        self.subtitle_lbl.setText(t("app_subtitle", lang))
        self.api_lbl.setText(t("gemini_api_key", lang))
        self.save_key_btn.setText(t("save_key", lang))
        self.guide_btn.setText(t("api_guide_btn", lang))
        self.settings_btn.setText(f"⚙ {t('settings_btn', lang)}")
        self.about_btn.setText(t("about_btn", lang))
        self.zoom_lbl.setText(t("zoom_label", lang))

        if lang == "en":
            self.lang_btn.setText("🌐 English")
        else:
            self.lang_btn.setText("🌐 বাংলা")

        self.paste_btn.setText(t("paste_btn", lang))
        self.proofread_btn.setText(t("proofread_btn", lang))
        if hasattr(self, "polish_btn"):
            self.polish_btn.setText(t("polish_btn", lang))
        self.clear_btn.setText(t("clear_btn", lang))
        self.copy_btn.setText(t("copy_btn", lang))
        self.replace_btn.setText(t("replace_btn", lang))

        self.tabs.setTabText(0, t("tab_side_by_side", lang))
        self.tabs.setTabText(1, t("tab_inline_diff", lang))
        self.tabs.setTabText(2, t("tab_changes_list", lang))
        self.tabs.setTabText(3, t("tab_sentence_polish", lang))

        self.orig_header.setText(t("orig_header", lang))
        self.corr_header.setText(t("corr_header", lang))
        self.inline_header.setText(t("inline_header", lang))
        self.table_instruction.setText(t("table_instruction", lang))
        self.accept_all_btn.setText(t("accept_all", lang))
        self.reject_all_btn.setText(t("reject_all", lang))
        self.exclude_foreign_btn.setText(t("exclude_foreign_btn", lang))

        if hasattr(self, "sentence_instruction"):
            self.sentence_instruction.setText(t("tab_sentence_polish", lang))
        if hasattr(self, "accept_all_sentences_btn"):
            self.accept_all_sentences_btn.setText(t("accept_all", lang))
        if hasattr(self, "reject_all_sentences_btn"):
            self.reject_all_sentences_btn.setText(t("reject_all", lang))

        self.changes_table.setHorizontalHeaderLabels([
            t("col_keep", lang),
            t("col_original", lang),
            t("col_suggested", lang),
            t("col_type", lang)
        ])

        if hasattr(self, "sentence_table"):
            self.sentence_table.setHorizontalHeaderLabels([
                t("col_keep", lang),
                t("col_sentence_original", lang),
                t("col_sentence_polished", lang),
                t("col_sentence_reason", lang)
            ])

        self.update_shortcut_status()
        self.update_api_status_banner()

        if self.last_diff_result:
            self.populate_changes_table(self.last_diff_result)
            self.refresh_views()
        else:
            self.stats_label.setText(t("stats_ready", lang))

    def toggle_language(self):
        """Toggle between English and Bangla."""
        self.lang = "bn" if self.lang == "en" else "en"
        config = load_config()
        config["ui_language"] = self.lang
        save_config(config)
        self.apply_language()

    def apply_theme(self, theme_mode: str):
        """Apply theme ('light', 'dark', or 'system') dynamically."""
        self.theme_mode = theme_mode
        self.effective_theme = get_effective_theme(theme_mode)
        apply_win32_titlebar_theme(self, self.effective_theme)
        self.setStyleSheet(get_window_stylesheet(self.effective_theme, BANGLA_FONT))
        self.update_theme_styles()
        self.update_api_status_banner()
        if self.last_diff_result:
            self.populate_changes_table(self.last_diff_result)
            self.refresh_views()

    def update_theme_styles(self):
        """Update inline widget colors based on active effective theme."""
        is_dark = (self.effective_theme == "dark")
        if is_dark:
            self.api_lbl.setStyleSheet("font-weight: 600; color: #94a3b8;")
            self.zoom_lbl.setStyleSheet("font-weight: 600; color: #94a3b8; font-size: 13px;")
            self.orig_header.setStyleSheet("font-weight: bold; color: #f87171;")
            self.corr_header.setStyleSheet("font-weight: bold; color: #4ade80;")
            self.inline_header.setStyleSheet("font-weight: bold; color: #cbd5e1;")
            self.table_instruction.setStyleSheet("font-weight: 600; color: #94a3b8;")
            self.stats_label.setStyleSheet("color: #94a3b8; font-weight: 600;")
            self.shortcut_status_label.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 12.5px;")
            self.feedback_label.setStyleSheet("color: #4ade80; font-weight: 600; padding-right: 10px;")
            self.progress_log_lbl.setStyleSheet("color: #60a5fa; font-weight: 600; font-size: 12px; margin-left: 6px;")
            if hasattr(self, "status_bar_separator"):
                self.status_bar_separator.setStyleSheet("color: #64748b; font-weight: 400;")
        else:
            self.api_lbl.setStyleSheet("font-weight: 600; color: #475569;")
            self.zoom_lbl.setStyleSheet("font-weight: 600; color: #475569; font-size: 13px;")
            self.orig_header.setStyleSheet("font-weight: bold; color: #dc2626;")
            self.corr_header.setStyleSheet("font-weight: bold; color: #16a34a;")
            self.inline_header.setStyleSheet("font-weight: bold; color: #334155;")
            self.table_instruction.setStyleSheet("font-weight: 600; color: #475569;")
            self.stats_label.setStyleSheet("color: #475569; font-weight: 600;")
            self.shortcut_status_label.setStyleSheet("color: #334155; font-weight: 600; font-size: 12.5px;")
            self.feedback_label.setStyleSheet("color: #16a34a; font-weight: 600; padding-right: 10px;")
            self.progress_log_lbl.setStyleSheet("color: #2563eb; font-weight: 600; font-size: 12px; margin-left: 6px;")
            if hasattr(self, "status_bar_separator"):
                self.status_bar_separator.setStyleSheet("color: #94a3b8; font-weight: 400;")

    def open_api_guide(self):
        """Show API key instructions dialog."""
        dialog = ApiGuideDialog(self, lang=self.lang, theme=self.theme_mode)
        dialog.exec()

    def open_about_dialog(self):
        """Show About Dialog with version, developer attribution, and portfolio."""
        dialog = AboutDialog(self, lang=self.lang, theme=self.theme_mode)
        dialog.exec()

    def update_api_status_banner(self):
        """Update top banner based on API key validity and active theme."""
        is_dark = (self.effective_theme == "dark")
        if self.engine_manager.is_gemini_available():
            self.status_banner.setText(t("api_ready", self.lang))
            if is_dark:
                self.status_banner.setStyleSheet(
                    "background-color: #064e3b; color: #6ee7b7; border: 1px solid #047857; "
                    "border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 500;"
                )
            else:
                self.status_banner.setStyleSheet(
                    "background-color: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; "
                    "border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 500;"
                )
        else:
            self.status_banner.setText(t("api_missing", self.lang))
            if is_dark:
                self.status_banner.setStyleSheet(
                    "background-color: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; "
                    "border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 500;"
                )
            else:
                self.status_banner.setStyleSheet(
                    "background-color: #fef2f2; color: #991b1b; border: 1px solid #fecaca; "
                    "border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 500;"
                )

    def save_api_key(self):
        """Save entered API key after user confirmation."""
        key = self.api_key_input.text().strip()
        msg = t("confirm_save_key_msg", self.lang) if key else t("confirm_clear_key_msg", self.lang)
        reply = show_themed_message_box(
            self,
            "question",
            t("confirm_save_key_title", self.lang),
            msg,
            effective_theme=self.effective_theme,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.engine_manager.set_gemini_api_key(key)
        self.update_api_status_banner()
        if key:
            self.show_feedback(t("api_saved", self.lang))
        else:
            self.show_feedback(t("api_cleared", self.lang))

    def _apply_uniform_line_spacing(self, widget: QTextEdit) -> None:
        """Apply identical 135% proportional line height and zero paragraph margins across all blocks."""
        doc = widget.document()
        doc.setDocumentMargin(8)
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        block_fmt = QTextBlockFormat()
        line_height_type = getattr(
            QTextBlockFormat.LineHeightTypes, "ProportionalHeight", 1
        ) if hasattr(QTextBlockFormat, "LineHeightTypes") else 1
        block_fmt.setLineHeight(135.0, int(getattr(line_height_type, "value", line_height_type)))
        block_fmt.setTopMargin(0)
        block_fmt.setBottomMargin(0)
        cursor.mergeBlockFormat(block_fmt)

    def _set_orig_plain_text(self, text: str) -> None:
        """Set plain text in orig_edit with clean formatting and uniform 135% line spacing."""
        self.orig_edit.blockSignals(True)
        self.orig_edit.document().clear()
        self.orig_edit.setCurrentCharFormat(QTextCharFormat())
        if text:
            is_dark = (getattr(self, "effective_theme", "light") == "dark")
            text_color = "#f8fafc" if is_dark else "#0f172a"
            line_css = "line-height: 1.35; margin: 0; padding: 0;"
            escaped = html.escape(text).replace("\n", "<br/>")
            self.orig_edit.setHtml(
                f"<div style='font-family: \"{BANGLA_FONT}\"; font-size: {self.editor_font_size}pt; color: {text_color}; {line_css}'>"
                f"{escaped}</div>"
            )
        else:
            self.orig_edit.setPlainText("")
        self._apply_uniform_line_spacing(self.orig_edit)
        self.orig_edit.blockSignals(False)

    def _get_orig_plain_text(self) -> str:
        """Return plain text from orig_edit with normalized newlines."""
        return self.orig_edit.toPlainText().replace("\u2028", "\n").replace("\u2029", "\n")

    def set_input_text(self, text: str):
        if is_bijoy_text(text):
            logger.info("Bijoy/SutonnyMJ text detected in set_input_text. Auto-converting to Unicode...")
            text = convert_bijoy_to_unicode(text)
        self._set_orig_plain_text(text)
        self.run_proofread()

    def paste_from_clipboard(self):
        text = ClipboardManager.get_text()
        if text:
            if is_bijoy_text(text):
                logger.info("Bijoy/SutonnyMJ text detected in clipboard. Auto-converting to Unicode...")
                text = convert_bijoy_to_unicode(text)
            self._set_orig_plain_text(text)
            self.run_proofread()
        else:
            self.show_feedback(t("no_text_feedback", self.lang))

    def set_actions_enabled(self, enabled: bool):
        """Enable or disable action buttons during background processing."""
        self.proofread_btn.setEnabled(enabled)
        if hasattr(self, "polish_btn"):
            self.polish_btn.setEnabled(enabled)
        self.paste_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.copy_btn.setEnabled(enabled)
        self.replace_btn.setEnabled(enabled)
        self.save_key_btn.setEnabled(enabled)
        self.lang_btn.setEnabled(enabled)

    def run_proofread(self):
        """Execute proofreading using Gemini AI (with instant offline Bijoy-to-Unicode conversion if needed)."""
        original_text = self._get_orig_plain_text().strip()
        if not original_text:
            self.stats_label.setText(t("no_input_warn", self.lang))
            self.corr_browser.clear()
            self.inline_browser.clear()
            self.changes_table.setRowCount(0)
            return

        if is_bijoy_text(original_text):
            logger.info("Bijoy/SutonnyMJ text detected in input editor. Auto-converting to Unicode...")
            original_text = convert_bijoy_to_unicode(original_text)
            self._set_orig_plain_text(original_text)

        if not self.engine_manager.is_internet_available():
            show_themed_message_box(
                self,
                "warning",
                t("no_internet_title", self.lang),
                t("no_internet_msg", self.lang),
                effective_theme=self.effective_theme,
            )
            return

        if not self.engine_manager.is_gemini_available():
            show_themed_message_box(
                self,
                "warning",
                t("api_missing_warn_title", self.lang),
                t("api_missing_warn_msg", self.lang),
                effective_theme=self.effective_theme,
            )
            return

        # Disconnect any previous worker so stale signals cannot interfere
        if self.worker is not None:
            try:
                self.worker.progress_signal.disconnect(self.on_worker_progress)
                self.worker.finished_signal.disconnect(self.on_worker_finished)
                self.worker.error_signal.disconnect(self.on_worker_error)
            except Exception:
                pass

        # Disable buttons and show progress bar (normal cursor maintained, no freeze)
        self.set_actions_enabled(False)
        if hasattr(self, "status_bar_separator"):
            self.status_bar_separator.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_log_lbl.setVisible(True)
        self.progress_log_lbl.setText(t("progress_starting", self.lang))
        self.update_shortcut_status()

        # Launch worker thread
        self.worker = ProofreadWorker(
            self.engine_manager,
            original_text,
            self.lang,
            is_dark=(self.effective_theme == "dark")
        )
        self.worker.progress_signal.connect(self.on_worker_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.start()

    def on_worker_progress(self, message: str):
        """Update live status message from background thread."""
        if hasattr(self, "status_bar_separator"):
            self.status_bar_separator.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_log_lbl.setVisible(True)
        self.progress_log_lbl.setText(message)

    def on_input_text_changed(self):
        """Reset sequence guardrail when input text is modified."""
        self.spelling_checked = False

    def on_worker_finished(self, corrected_text: str, diff_result: DiffResult):
        """Called when background worker finishes successfully."""
        self.last_diff_result = diff_result
        self.accepted_change_ids = {c.change_id for c in diff_result.changes}
        self.spelling_checked = True

        self.populate_changes_table(diff_result)
        self.refresh_views()

        # Clean up UI state and keep bottom-left shortcut status visible
        if hasattr(self, "status_bar_separator"):
            self.status_bar_separator.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_log_lbl.setVisible(False)
        self.progress_log_lbl.setText("")
        self.set_actions_enabled(True)
        self.update_shortcut_status()

        # Reset scrollbars to top on completion for seamless aligned reading
        self.orig_edit.verticalScrollBar().setValue(0)
        self.corr_browser.verticalScrollBar().setValue(0)

    def on_worker_error(self, err_msg: str):
        """Called when background worker encounters an error."""
        if hasattr(self, "status_bar_separator"):
            self.status_bar_separator.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_log_lbl.setVisible(False)
        self.progress_log_lbl.setText("")
        self.set_actions_enabled(True)
        self.update_shortcut_status()

        formatted_msg = format_gemini_error(err_msg, self.lang)
        show_themed_message_box(
            self,
            "critical",
            t("error_title", self.lang),
            formatted_msg,
            effective_theme=self.effective_theme,
        )

    def on_polish_worker_error(self, err_msg: str):
        """Called when sentence polish background worker encounters an error."""
        if hasattr(self, "status_bar_separator"):
            self.status_bar_separator.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_log_lbl.setVisible(False)
        self.progress_log_lbl.setText("")
        self.set_actions_enabled(True)
        self.update_shortcut_status()

        formatted_msg = format_gemini_error(err_msg, self.lang)
        show_themed_message_box(
            self,
            "warning",
            t("error_title", self.lang),
            formatted_msg,
            effective_theme=self.effective_theme,
        )

    def run_sentence_polish(self):
        """Execute AI Sentence Polish with strict sequence guardrail."""
        original_text = self._get_orig_plain_text().strip()
        if not original_text:
            show_themed_message_box(
                self,
                "information",
                t("error_title", self.lang),
                t("no_input_warn", self.lang),
                effective_theme=self.effective_theme,
            )
            return

        # Sequence Guardrail check:
        if not self.spelling_checked:
            show_themed_message_box(
                self,
                "warning",
                t("guardrail_title", self.lang),
                t("guardrail_msg", self.lang),
                effective_theme=self.effective_theme,
            )
            return

        # Sentence Polish requires internet connection
        if not self.engine_manager.is_internet_available():
            show_themed_message_box(
                self,
                "warning",
                t("no_internet_title", self.lang),
                t("no_internet_msg", self.lang),
                effective_theme=self.effective_theme,
            )
            return

        # Disconnect previous worker
        if self.polish_worker is not None:
            try:
                self.polish_worker.progress_signal.disconnect(self.on_worker_progress)
                self.polish_worker.finished_signal.disconnect(self.on_polish_worker_finished)
                self.polish_worker.error_signal.disconnect(self.on_polish_worker_error)
            except Exception:
                pass

        self.set_actions_enabled(False)
        if hasattr(self, "status_bar_separator"):
            self.status_bar_separator.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_log_lbl.setVisible(True)
        self.progress_log_lbl.setText(t("progress_polishing", self.lang))
        self.update_shortcut_status()

        input_for_polish = self.corr_browser.toPlainText().strip() or original_text

        self.polish_worker = PolishWorker(self.engine_manager, input_for_polish, self.lang)
        self.polish_worker.progress_signal.connect(self.on_worker_progress)
        self.polish_worker.finished_signal.connect(self.on_polish_worker_finished)
        self.polish_worker.error_signal.connect(self.on_polish_worker_error)
        self.polish_worker.start()

    def on_polish_worker_finished(self, polish_result: SentencePolishResult):
        """Called when sentence polish finishes successfully."""
        self.last_polish_result = polish_result
        self.populate_sentence_table(polish_result)

        # Switch to dedicated Sentence Polish tab
        self.tabs.setCurrentIndex(3)

        # Update corrected browser and diff view
        self.corr_browser.setPlainText(polish_result.full_polished_text)
        self.render_inline_diff(self._get_orig_plain_text(), polish_result.full_polished_text)

        if hasattr(self, "status_bar_separator"):
            self.status_bar_separator.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_log_lbl.setVisible(False)
        self.progress_log_lbl.setText("")
        self.set_actions_enabled(True)
        self.update_shortcut_status()
        self.show_feedback(t("polish_done", self.lang))

    def populate_sentence_table(self, polish_result: SentencePolishResult):
        """Populate dedicated sentence polish comparison view with Keep/Reject checkboxes."""
        self.sentence_table.blockSignals(True)
        self.sentence_table.setRowCount(0)
        self.accepted_sentence_ids = {c.change_id for c in polish_result.changes}

        bangla_font = create_bangla_font(max(11, self.editor_font_size))
        is_dark = (self.effective_theme == "dark")
        orig_color = QColor("#f87171" if is_dark else "#dc2626")
        pol_color = QColor("#4ade80" if is_dark else "#16a34a")

        for row_idx, change in enumerate(polish_result.changes):
            self.sentence_table.insertRow(row_idx)

            # Centered proper modern QCheckBox widget
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            chk = QCheckBox()
            chk.setChecked(change.change_id in self.accepted_sentence_ids)
            chk.toggled.connect(lambda checked, cid=change.change_id: self.on_sentence_toggled(cid, checked))
            chk_layout.addWidget(chk)
            self.sentence_table.setCellWidget(row_idx, 0, chk_widget)

            orig_item = QTableWidgetItem(change.original)
            orig_item.setFont(bangla_font)
            orig_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            orig_item.setForeground(QBrush(orig_color))
            orig_item.setToolTip(change.original)
            self.sentence_table.setItem(row_idx, 1, orig_item)

            pol_item = QTableWidgetItem(change.polished)
            pol_item.setFont(bangla_font)
            pol_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            pol_item.setForeground(QBrush(pol_color))
            pol_item.setToolTip(change.polished)
            self.sentence_table.setItem(row_idx, 2, pol_item)

            reason_item = QTableWidgetItem(change.reason)
            reason_item.setFont(bangla_font)
            reason_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            reason_item.setToolTip(change.reason)
            self.sentence_table.setItem(row_idx, 3, reason_item)

        self.sentence_table.resizeRowsToContents()
        self.sentence_table.blockSignals(False)

    def render_inline_diff(self, orig: str, corr: str):
        """Render inline and side-by-side diff between orig and corr text."""
        diff_res = DiffHighlighter.compute_diff(orig, corr, is_dark=(self.effective_theme == "dark"))
        self.last_diff_result = diff_res
        self.accepted_change_ids = {c.change_id for c in diff_res.changes}
        self.refresh_views()

    def on_sentence_toggled(self, change_id: int, is_checked: bool):
        """Handle toggling Keep/Reject checkbox in sentence polish table."""
        if is_checked:
            self.accepted_sentence_ids.add(change_id)
        else:
            self.accepted_sentence_ids.discard(change_id)
        self.apply_sentence_changes()

    def apply_sentence_changes(self):
        """Reconstruct polished text based on accepted sentence selections."""
        if not self.last_polish_result:
            return
        text = self.last_polish_result.full_polished_text
        for change in self.last_polish_result.changes:
            if change.change_id not in self.accepted_sentence_ids:
                if change.polished in text:
                    text = text.replace(change.polished, change.original, 1)
        self.corr_browser.setPlainText(text)
        self.render_inline_diff(self._get_orig_plain_text(), text)

    def accept_all_sentences(self):
        """Accept all sentence refinements."""
        if not self.last_polish_result:
            return
        self.accepted_sentence_ids = {c.change_id for c in self.last_polish_result.changes}
        for row in range(self.sentence_table.rowCount()):
            w = self.sentence_table.cellWidget(row, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(True)
                    chk.blockSignals(False)
        self.apply_sentence_changes()

    def reject_all_sentences(self):
        """Reject all sentence refinements and revert to pre-polished text."""
        if not self.last_polish_result:
            return
        self.accepted_sentence_ids.clear()
        for row in range(self.sentence_table.rowCount()):
            w = self.sentence_table.cellWidget(row, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(False)
                    chk.blockSignals(False)
        self.apply_sentence_changes()
        self.sentence_table.blockSignals(False)
        self.apply_sentence_changes()

    def populate_changes_table(self, diff_result: DiffResult):
        """Populate the changes table with interactive checkboxes."""
        self.changes_table.blockSignals(True)
        self.changes_table.setRowCount(0)

        type_map = {
            "replace": t("type_replace", self.lang),
            "insert": t("type_insert", self.lang),
            "delete": t("type_delete", self.lang),
        }

        for row, change in enumerate(diff_result.changes):
            self.changes_table.insertRow(row)

            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(12, 0, 12, 0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            chk = QCheckBox()
            chk.setChecked(change.change_id in self.accepted_change_ids)
            chk.toggled.connect(lambda checked, cid=change.change_id: self.on_change_toggled(cid, checked))
            chk_layout.addWidget(chk)

            orig_item = QTableWidgetItem(change.original)
            corr_item = QTableWidgetItem(change.corrected)

            classification = get_word_classification(change.original, change.corrected)
            is_punct_only = not is_word(change.original) and not is_word(change.corrected)
            is_dark = (self.effective_theme == "dark")

            if classification == "arabic":
                type_text = t("type_arabic", self.lang)
                type_item = QTableWidgetItem(type_text)
                type_item.setForeground(QColor("#c084fc" if is_dark else "#7c3aed"))
            elif classification == "foreign":
                type_text = t("type_foreign", self.lang)
                type_item = QTableWidgetItem(type_text)
                type_item.setForeground(QColor("#38bdf8" if is_dark else "#0284c7"))
            elif is_punct_only:
                type_text = t("type_punct", self.lang)
                type_item = QTableWidgetItem(type_text)
                type_item.setForeground(QColor("#fb923c" if is_dark else "#ea580c"))
            else:
                type_text = type_map.get(change.change_type, change.change_type)
                type_item = QTableWidgetItem(type_text)
                if is_dark:
                    type_item.setForeground(QColor("#94a3b8"))

            green_color = QColor("#4ade80" if is_dark else "#16a34a")
            red_color = QColor("#f87171" if is_dark else "#dc2626")

            if change.change_type == "replace":
                corr_item.setForeground(green_color)
                orig_item.setForeground(red_color)
            elif change.change_type == "insert":
                corr_item.setForeground(green_color)
            elif change.change_type == "delete":
                orig_item.setForeground(red_color)
            else:
                if is_dark:
                    orig_item.setForeground(QColor("#f8fafc"))
                    corr_item.setForeground(QColor("#f8fafc"))

            table_font = create_bangla_font(self.editor_font_size)
            orig_item.setFont(table_font)
            corr_item.setFont(table_font)
            type_item.setFont(table_font)

            self.changes_table.setCellWidget(row, 0, chk_widget)
            self.changes_table.setItem(row, 1, orig_item)
            self.changes_table.setItem(row, 2, corr_item)
            self.changes_table.setItem(row, 3, type_item)

        self.changes_table.blockSignals(False)

    def on_change_toggled(self, change_id: int, checked: bool):
        if checked:
            self.accepted_change_ids.add(change_id)
        else:
            self.accepted_change_ids.discard(change_id)
        self.refresh_views()

    def accept_all_changes(self):
        if not self.last_diff_result:
            return
        self.accepted_change_ids = {c.change_id for c in self.last_diff_result.changes}
        self.populate_changes_table(self.last_diff_result)
        self.refresh_views()

    def reject_all_changes(self):
        if not self.last_diff_result:
            return
        self.accepted_change_ids.clear()
        self.populate_changes_table(self.last_diff_result)
        self.refresh_views()

    def exclude_foreign_words(self):
        """Uncheck Arabic/Islamic loanwords with disputed spellings while keeping native corrections."""
        if not self.last_diff_result:
            return

        for change in self.last_diff_result.changes:
            if is_arabic_word(change.original, change.corrected) or is_foreign_word(change.original, change.corrected):
                self.accepted_change_ids.discard(change.change_id)

        self.populate_changes_table(self.last_diff_result)
        self.refresh_views()
        self.show_feedback(t("foreign_excluded_feedback", self.lang))

    def refresh_views(self):
        """Re-render views based on accepted suggestions and active theme."""
        if not self.last_diff_result:
            return

        is_dark = (self.effective_theme == "dark")
        updated_diff = DiffHighlighter.render_from_opcodes(
            orig_tokens=self.last_diff_result.orig_tokens,
            corr_tokens=self.last_diff_result.corr_tokens,
            opcodes=self.last_diff_result.opcodes,
            changes=self.last_diff_result.changes,
            accepted_ids=self.accepted_change_ids,
            is_dark=is_dark
        )
        self.last_diff_result = updated_diff

        line_css = "line-height: 1.35; margin: 0; padding: 0;"
        text_color = "#f8fafc" if is_dark else "#0f172a"
        orig_scroll = self.orig_edit.verticalScrollBar().value()
        corr_scroll = self.corr_browser.verticalScrollBar().value()

        self.orig_edit.blockSignals(True)
        self.orig_edit.setHtml(
            f"<div style='font-family: \"{BANGLA_FONT}\"; font-size: {self.editor_font_size}pt; color: {text_color}; {line_css}'>"
            f"{updated_diff.original_html}</div>"
        )
        self._apply_uniform_line_spacing(self.orig_edit)
        self.orig_edit.blockSignals(False)

        self.corr_browser.setHtml(
            f"<div style='font-family: \"{BANGLA_FONT}\"; font-size: {self.editor_font_size}pt; color: {text_color}; {line_css}'>"
            f"{updated_diff.corrected_html}</div>"
        )
        self._apply_uniform_line_spacing(self.corr_browser)

        self.inline_browser.setHtml(
            f"<div style='font-family: \"{BANGLA_FONT}\"; font-size: {self.editor_font_size}pt; color: {text_color}; {line_css}'>"
            f"{updated_diff.inline_html}</div>"
        )
        self._apply_uniform_line_spacing(self.inline_browser)

        self.orig_edit.verticalScrollBar().setValue(orig_scroll)
        self.corr_browser.verticalScrollBar().setValue(corr_scroll)

        stats = updated_diff.stats
        self.stats_label.setText(
            t("stats_format", self.lang,
              orig=stats["original_words"],
              total=stats["total_suggestions"],
              acc=stats["accepted_changes"],
              rej=stats["rejected_changes"])
        )

    def get_corrected_text(self) -> str:
        if self.last_diff_result:
            return self.last_diff_result.corrected_text
        return self._get_orig_plain_text()

    def copy_corrected_text(self):
        corrected = self.get_corrected_text()
        if corrected:
            ClipboardManager.set_text(corrected)
            self.show_feedback(t("copied_feedback", self.lang))
        else:
            self.show_feedback(t("no_text_feedback", self.lang))

    def replace_in_active_app(self):
        corrected = self.get_corrected_text()
        if not corrected:
            self.show_feedback(t("no_replace_feedback", self.lang))
            return

        # Populate clipboard once BEFORE minimizing so Adobe Illustrator pre-converts
        # the clipboard on WM_ACTIVATEAPP (identical to manual Copy + Ctrl+V -> 1 Undo step)
        ClipboardManager.set_text(corrected)
        self.show_feedback(t("replacing_feedback", self.lang))
        self.replace_requested.emit(corrected)

        self.showMinimized()
        QTimer.singleShot(300, lambda: ClipboardManager.paste_into_active_window(corrected, set_clipboard=False))

    def clear_all(self):
        self.orig_edit.document().clear()
        self.orig_edit.setCurrentCharFormat(QTextCharFormat())
        self._apply_uniform_line_spacing(self.orig_edit)
        self.corr_browser.clear()
        self.inline_browser.clear()
        self.changes_table.setRowCount(0)
        self.accepted_change_ids.clear()
        if hasattr(self, "sentence_table"):
            self.sentence_table.setRowCount(0)
            self.accepted_sentence_ids.clear()
            self.last_polish_result = None
        self.spelling_checked = False
        self.stats_label.setText(t("stats_ready", self.lang))
        self.last_diff_result = None

    def show_feedback(self, message: str, duration_ms: int = 3000):
        self.feedback_label.setText(message)
        QTimer.singleShot(duration_ms, lambda: self.feedback_label.setText(""))

    def apply_font_size(self, size: int):
        """Update editor and table font size within range 10pt to 22pt and persist in config."""
        self.editor_font_size = max(10, min(22, size))
        bangla_font = create_bangla_font(self.editor_font_size)
        self.orig_edit.setFont(bangla_font)
        self.corr_browser.setFont(bangla_font)
        self.inline_browser.setFont(bangla_font)
        self.zoom_reset_btn.setText(f"{self.editor_font_size}pt")

        # Dynamically scale Changes List table
        self.changes_table.setFont(bangla_font)
        self.changes_table.horizontalHeader().setFont(create_bangla_font(max(10, self.editor_font_size - 1)))
        row_height = max(30, int(self.editor_font_size * 2.3))
        self.changes_table.verticalHeader().setDefaultSectionSize(row_height)
        for r in range(self.changes_table.rowCount()):
            for c in range(1, 4):
                item = self.changes_table.item(r, c)
                if item:
                    item.setFont(bangla_font)

        config = load_config()
        config["editor_font_size"] = self.editor_font_size
        save_config(config)

        if self.last_diff_result:
            self.refresh_views()

    def increase_font_size(self):
        self.apply_font_size(self.editor_font_size + 1)

    def decrease_font_size(self):
        self.apply_font_size(self.editor_font_size - 1)

    def reset_font_size(self):
        self.apply_font_size(14)

    def open_settings_dialog(self):
        """Open settings dialog to configure Gemini API, shortcuts, autostart, tray, and theme."""
        config = load_config()
        dlg = SettingsDialog(parent=self, config=config, lang=self.lang, theme=self.theme_mode)
        if dlg.exec():
            save_config(dlg.config)
            new_key = dlg.config.get("gemini_api_key", "")
            if hasattr(self.engine_manager, "set_gemini_api_key"):
                self.engine_manager.set_gemini_api_key(new_key)
            elif hasattr(self.engine_manager, "set_api_key"):
                self.engine_manager.set_api_key(new_key)
            self.api_key_input.setText(new_key)

            # Apply updated theme if changed
            new_theme = dlg.config.get("theme", "system")
            if new_theme != self.theme_mode:
                self.apply_theme(new_theme)

            # Apply updated global shortcut if changed
            new_shortcut = (dlg.config.get("shortcut", "ctrl+alt+b") or "ctrl+alt+b").strip().lower()
            if new_shortcut not in ("ctrl+alt+b", "ctrl+alt+z", "ctrl+alt+x"):
                new_shortcut = "ctrl+alt+b"
            self.shortcut_changed.emit(new_shortcut)
            self.update_shortcut_status(new_shortcut)

            self.show_feedback(t("api_saved", self.lang))

    def closeEvent(self, event):
        """Gracefully minimize to system tray instead of closing when enabled."""
        config = load_config()
        if config.get("minimize_to_tray_on_close", True):
            event.ignore()
            self.hide()
        else:
            event.accept()

    def changeEvent(self, event):
        """Standard window state change: preserve normal minimize to taskbar."""
        super().changeEvent(event)
