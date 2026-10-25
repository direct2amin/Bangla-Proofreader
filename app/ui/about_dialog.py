"""About Dialog displaying application metadata, developer profile, and portfolio link."""

from __future__ import annotations

import os
import webbrowser

try:
    from PyQt6.QtCore import Qt, QUrl
    from PyQt6.QtGui import QPixmap, QDesktopServices, QIcon
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
    )
except ImportError:
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QPixmap, QDesktopServices, QIcon
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
    )

from app.core.theme import get_effective_theme, get_about_stylesheet, apply_win32_titlebar_theme
from app.core.assets import get_asset_path
from app.utils.i18n import t

PORTFOLIO_URL = "https://direct2amin.github.io/aminsweb/"
LOGO_ICON_PATH = get_asset_path("logo_icon.png")
LOGO_ICO_PATH = get_asset_path("logo.ico")

ABOUT_STYLESHEET = """
QDialog {
    background-color: #ffffff;
    color: #0f172a;
    font-family: "Nirmala UI";
}
QLabel#AppTitle {
    font-size: 18px;
    font-weight: bold;
    color: #0b663b;
}
QLabel#VersionBadge {
    background-color: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}
QFrame#InfoCard {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px;
}
QLabel.InfoLabel {
    color: #334155;
    font-size: 13px;
    line-height: 1.5;
}
QLabel.FieldTitle {
    font-weight: bold;
    color: #0f172a;
    font-size: 13px;
}
QPushButton#LinkBtn {
    color: #0b663b;
    font-weight: 600;
    font-size: 13px;
    text-decoration: underline;
    background: transparent;
    border: none;
    text-align: left;
    padding: 0;
}
QPushButton#LinkBtn:hover {
    color: #047857;
}
QPushButton#CloseBtn {
    background-color: #0b663b;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 24px;
    border-radius: 6px;
    border: none;
}
QPushButton#CloseBtn:hover {
    background-color: #08502e;
}
"""


class AboutDialog(QDialog):
    """Modern modal dialog presenting app version, developer attribution, and portfolio."""

    def __init__(self, parent=None, lang: str = "en", theme: str = "system"):
        super().__init__(parent)
        self.lang = lang
        self.theme_mode = theme
        self.effective_theme = get_effective_theme(theme)

        # English title on Windows title bar to prevent DWM tofu square rendering
        self.setWindowTitle("About Bangla Proofreader")
        self.resize(540, 430)
        self.setMinimumSize(540, 430)
        apply_win32_titlebar_theme(self, self.effective_theme)
        self.setStyleSheet(get_about_stylesheet(self.effective_theme))

        if os.path.exists(LOGO_ICO_PATH):
            self.setWindowIcon(QIcon(LOGO_ICO_PATH))
        elif os.path.exists(LOGO_ICON_PATH):
            self.setWindowIcon(QIcon(LOGO_ICON_PATH))

        self.init_ui()

    @staticmethod
    def open_portfolio():
        """Open developer portfolio in default web browser."""
        url = QUrl(PORTFOLIO_URL)
        if not QDesktopServices.openUrl(url):
            webbrowser.open(PORTFOLIO_URL)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # 1. Header with App Logo
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(6)

        if os.path.exists(LOGO_ICON_PATH):
            logo_lbl = QLabel()
            pix = QPixmap(LOGO_ICON_PATH).scaled(
                72, 72,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(logo_lbl)

        title_lbl = QLabel(t("about_app_name", self.lang))
        title_lbl.setObjectName("AppTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_lbl)

        version_lbl = QLabel(t("about_version", self.lang))
        version_lbl.setObjectName("VersionBadge")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version_lbl)

        layout.addLayout(header_layout)

        # 2. Main Details Card
        info_card = QFrame()
        info_card.setObjectName("InfoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(14, 12, 14, 12)

        # Description
        desc_lbl = QLabel(t("about_description", self.lang))
        desc_lbl.setProperty("class", "InfoLabel")
        desc_lbl.setWordWrap(True)
        info_layout.addWidget(desc_lbl)

        # Divider line
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div_color = "#334155" if self.effective_theme == "dark" else "#e2e8f0"
        div.setStyleSheet(f"color: {div_color}; background-color: {div_color}; height: 1px;")
        info_layout.addWidget(div)

        # Developer / Publisher
        dev_row = QHBoxLayout()
        dev_title = QLabel(t("about_developer_label", self.lang))
        dev_title.setProperty("class", "FieldTitle")
        dev_val = QLabel(t("about_developer_name", self.lang))
        dev_color = "#34d399" if self.effective_theme == "dark" else "#0b663b"
        dev_val.setStyleSheet(f"color: {dev_color}; font-weight: bold; font-size: 13px;")
        dev_row.addWidget(dev_title)
        dev_row.addWidget(dev_val)
        dev_row.addStretch()
        info_layout.addLayout(dev_row)

        # Portfolio / GitHub Link
        port_row = QHBoxLayout()
        port_title = QLabel(t("about_portfolio_label", self.lang))
        port_title.setProperty("class", "FieldTitle")
        port_row.addWidget(port_title)

        link_btn = QPushButton("https://direct2amin.github.io/aminsweb/")
        link_btn.setObjectName("LinkBtn")
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.clicked.connect(self.open_portfolio)
        port_row.addWidget(link_btn, stretch=1)
        info_layout.addLayout(port_row)

        layout.addWidget(info_card)

        layout.addStretch()

        # 3. Close Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton(t("close_btn", self.lang))
        close_btn.setObjectName("CloseBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
