"""Theme engine providing Light Mode, Dark Mode, and System Theme matching."""

from __future__ import annotations

import sys
from typing import Dict, Any

BANGLA_FONT = "Nirmala UI"


def get_system_theme() -> str:
    """Detect if the operating system is using Dark or Light theme."""
    # Windows Registry check (most accurate on Windows)
    if sys.platform.startswith("win"):
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if val != 0 else "dark"
        except Exception:
            pass

    # Qt StyleHints fallback
    try:
        from PyQt6.QtGui import QGuiApplication
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorScheme"):
            from PyQt6.QtCore import Qt
            if hints.colorScheme() == Qt.ColorScheme.Dark:
                return "dark"
            elif hints.colorScheme() == Qt.ColorScheme.Light:
                return "light"
    except Exception:
        pass

    return "light"


def get_effective_theme(theme_mode: str = "system") -> str:
    """Resolve 'system', 'light', or 'dark' to effective 'light' or 'dark'."""
    if theme_mode == "system":
        return get_system_theme()
    return "dark" if theme_mode == "dark" else "light"


def get_window_stylesheet(effective_theme: str = "light", font_family: str = BANGLA_FONT) -> str:
    """Return main window QSS stylesheet for effective theme."""
    if effective_theme == "dark":
        return f"""
QMainWindow {{
    background-color: #0f172a;
    font-family: "{font_family}";
}}

QWidget {{
    color: #f8fafc;
    font-family: "{font_family}";
}}

QFrame#HeaderBar {{
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    padding: 8px 16px;
}}

QLabel#AppTitle {{
    font-size: 18px;
    font-weight: bold;
    color: #10b981;
    font-family: "{font_family}";
}}

QLabel#AppSubtitle {{
    font-size: 11.5px;
    color: #94a3b8;
    font-family: "{font_family}";
}}

QLineEdit {{
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    font-family: "{font_family}";
}}

QLineEdit:focus {{
    border: 1.5px solid #10b981;
}}

QTabWidget::pane {{
    border: 1px solid #334155;
    background: #1e293b;
    border-radius: 6px;
}}

QTabBar::tab {{
    background: #0f172a;
    color: #94a3b8;
    font-weight: 600;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-family: "{font_family}";
}}

QTabBar::tab:selected {{
    background: #1e293b;
    color: #34d399;
    border-bottom: 2px solid #10b981;
}}

QTextEdit, QTextBrowser {{
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 10px;
    font-family: "{font_family}";
}}

QTextEdit:focus, QTextBrowser:focus {{
    border: 1.5px solid #10b981;
}}

QSplitter {{
    background-color: transparent;
}}

QSplitter::handle {{
    background-color: transparent;
    width: 4px;
}}

QSplitter::handle:hover {{
    background-color: #064e3b;
}}

QPushButton {{
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
    border-radius: 6px;
    border: 1px solid #334155;
    background-color: #1e293b;
    color: #e2e8f0;
    font-family: "{font_family}";
}}

QPushButton:hover {{
    background-color: #334155;
    border-color: #475569;
}}

QPushButton:disabled {{
    background-color: #1e293b;
    color: #64748b;
    border-color: #334155;
}}

QPushButton#PrimaryBtn {{
    background-color: #0b663b;
    color: #ffffff;
    border: none;
    font-weight: bold;
}}

QPushButton#PrimaryBtn:hover {{
    background-color: #059669;
}}

QPushButton#PrimaryBtn:disabled {{
    background-color: #064e3b;
    color: #6ee7b7;
}}

QPushButton#SuccessBtn {{
    background-color: #15803d;
    color: #ffffff;
    border: none;
    font-weight: bold;
}}

QPushButton#SuccessBtn:hover {{
    background-color: #16a34a;
}}

QPushButton#SuccessBtn:disabled {{
    background-color: #14532d;
    color: #86efac;
}}

QPushButton#ExcludeArabicBtn {{
    background-color: #2e1065;
    color: #c4b5fd;
    border: 1px solid #6d28d9;
    font-weight: 600;
}}

QPushButton#ExcludeArabicBtn:hover {{
    background-color: #3b0764;
    border-color: #8b5cf6;
}}

QPushButton#LangBtn {{
    background-color: #1e293b;
    color: #f8fafc;
    font-weight: bold;
    border: 1px solid #334155;
    padding: 6px 14px;
}}

QPushButton#LangBtn:hover {{
    background-color: #334155;
}}

QTableWidget {{
    background-color: #0f172a;
    border: 1px solid #334155;
    gridline-color: #1e293b;
    color: #f8fafc;
    font-family: "{font_family}";
}}

QHeaderView::section {{
    background-color: #1e293b;
    font-weight: 600;
    color: #94a3b8;
    padding: 8px;
    border: 1px solid #334155;
    font-family: "{font_family}";
}}

QProgressBar {{
    border: 1px solid #334155;
    border-radius: 4px;
    text-align: center;
    background-color: #1e293b;
    height: 14px;
}}

QProgressBar::chunk {{
    background-color: #10b981;
    border-radius: 4px;
}}

#ZoomFrame {{
    background: transparent;
    border: none;
}}

#ZoomFrame QPushButton {{
    padding: 2px 4px;
    font-size: 12px;
    font-weight: 600;
}}

QStatusBar {{
    background-color: #1e293b;
    color: #cbd5e1;
    border-top: 1px solid #334155;
    font-size: 12.5px;
    font-weight: 600;
    padding: 2px 8px;
}}

QStatusBar QLabel {{
    color: #cbd5e1;
    font-size: 12.5px;
    font-weight: 600;
}}

QDialog, QMessageBox {{
    background-color: #1e293b;
    color: #f8fafc;
    font-family: "{font_family}";
}}

QMessageBox QLabel {{
    background-color: transparent;
    color: #f8fafc;
    font-size: 13.5px;
    font-weight: 500;
}}

QMessageBox QPushButton {{
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 20px;
    min-width: 68px;
    font-weight: 600;
}}

QMessageBox QPushButton:hover {{
    background-color: #475569;
    border-color: #64748b;
}}

QComboBox {{
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    font-family: "{font_family}";
}}

QComboBox:hover {{
    border-color: #10b981;
}}

QComboBox QAbstractItemView {{
    background-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #064e3b;
    selection-color: #34d399;
    border: 1px solid #334155;
}}
"""
    else:
        return f"""
QMainWindow {{
    background-color: #f8fafc;
    font-family: "{font_family}";
}}

QWidget {{
    color: #0f172a;
    font-family: "{font_family}";
}}

QFrame#HeaderBar {{
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 16px;
}}

QLabel#AppTitle {{
    font-size: 18px;
    font-weight: bold;
    color: #0b663b;
    font-family: "{font_family}";
}}

QLabel#AppSubtitle {{
    font-size: 11.5px;
    color: #64748b;
    font-family: "{font_family}";
}}

QLineEdit {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    font-family: "{font_family}";
}}

QLineEdit:focus {{
    border: 1.5px solid #0b663b;
}}

QTabWidget::pane {{
    border: 1px solid #e2e8f0;
    background: #ffffff;
    border-radius: 6px;
}}

QTabBar::tab {{
    background: #f1f5f9;
    color: #475569;
    font-weight: 600;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-family: "{font_family}";
}}

QTabBar::tab:selected {{
    background: #ffffff;
    color: #0b663b;
    border-bottom: 2px solid #0b663b;
}}

QTextEdit, QTextBrowser {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 10px;
    font-family: "{font_family}";
}}

QTextEdit:focus, QTextBrowser:focus {{
    border: 1.5px solid #0b663b;
}}

QSplitter {{
    background-color: transparent;
}}

QSplitter::handle {{
    background-color: transparent;
    width: 4px;
}}

QSplitter::handle:hover {{
    background-color: #d1fae5;
}}

QPushButton {{
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
    border-radius: 6px;
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
    color: #334155;
    font-family: "{font_family}";
}}

QPushButton:hover {{
    background-color: #f1f5f9;
    border-color: #94a3b8;
}}

QPushButton:disabled {{
    background-color: #e2e8f0;
    color: #94a3b8;
    border-color: #cbd5e1;
}}

QPushButton#PrimaryBtn {{
    background-color: #0b663b;
    color: #ffffff;
    border: none;
    font-weight: bold;
}}

QPushButton#PrimaryBtn:hover {{
    background-color: #08502e;
}}

QPushButton#PrimaryBtn:disabled {{
    background-color: #a7f3d0;
    color: #ffffff;
}}

QPushButton#SuccessBtn {{
    background-color: #16a34a;
    color: #ffffff;
    border: none;
    font-weight: bold;
}}

QPushButton#SuccessBtn:hover {{
    background-color: #15803d;
}}

QPushButton#SuccessBtn:disabled {{
    background-color: #86efac;
    color: #ffffff;
}}

QPushButton#ExcludeArabicBtn {{
    background-color: #f5f3ff;
    color: #6d28d9;
    border: 1px solid #c4b5fd;
    font-weight: 600;
}}

QPushButton#ExcludeArabicBtn:hover {{
    background-color: #ede9fe;
    border-color: #8b5cf6;
}}

QPushButton#LangBtn {{
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: bold;
    border: 1px solid #cbd5e1;
    padding: 6px 14px;
}}

QPushButton#LangBtn:hover {{
    background-color: #e2e8f0;
}}

QTableWidget {{
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    gridline-color: #f1f5f9;
    color: #0f172a;
    font-family: "{font_family}";
}}

QHeaderView::section {{
    background-color: #f8fafc;
    font-weight: 600;
    color: #475569;
    padding: 8px;
    border: 1px solid #e2e8f0;
    font-family: "{font_family}";
}}

QProgressBar {{
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    text-align: center;
    background-color: #f1f5f9;
    height: 14px;
}}

QProgressBar::chunk {{
    background-color: #0b663b;
    border-radius: 4px;
}}

#ZoomFrame {{
    background: transparent;
    border: none;
}}

#ZoomFrame QPushButton {{
    padding: 2px 4px;
    font-size: 12px;
    font-weight: 600;
}}

QStatusBar {{
    background-color: #f1f5f9;
    color: #334155;
    border-top: 1px solid #e2e8f0;
    font-size: 12.5px;
    font-weight: 600;
    padding: 2px 8px;
}}

QStatusBar QLabel {{
    color: #334155;
    font-size: 12.5px;
    font-weight: 600;
}}

QDialog, QMessageBox {{
    background-color: #ffffff;
    color: #0f172a;
    font-family: "{font_family}";
}}

QMessageBox QLabel {{
    background-color: transparent;
    color: #0f172a;
    font-size: 13.5px;
    font-weight: 500;
}}

QMessageBox QPushButton {{
    background-color: #f1f5f9;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 20px;
    min-width: 68px;
    font-weight: 600;
}}

QMessageBox QPushButton:hover {{
    background-color: #e2e8f0;
    border-color: #94a3b8;
}}

QComboBox {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    font-family: "{font_family}";
}}

QComboBox:hover {{
    border-color: #0b663b;
}}

QComboBox QAbstractItemView {{
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: #ecfdf5;
    selection-color: #065f46;
    border: 1px solid #cbd5e1;
}}
"""


def get_settings_stylesheet(effective_theme: str = "light", font_family: str = BANGLA_FONT) -> str:
    """Return Settings Dialog QSS stylesheet for effective theme."""
    if effective_theme == "dark":
        return f"""
QDialog {{
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "{font_family}";
}}

QGroupBox {{
    font-weight: bold;
    font-size: 13px;
    color: #10b981;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    padding-left: 14px;
    padding-right: 14px;
    padding-bottom: 14px;
    background-color: #1e293b;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: #34d399;
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 4px;
    font-weight: 600;
}}

QLabel {{
    color: #e2e8f0;
    font-size: 13px;
    font-weight: 500;
}}

QLineEdit {{
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1.5px solid #10b981;
}}

QComboBox {{
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}}

QComboBox:focus {{
    border: 1.5px solid #10b981;
}}

QComboBox QAbstractItemView {{
    background-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #0b663b;
    selection-color: #ffffff;
    border: 1px solid #334155;
}}

QCheckBox {{
    color: #f8fafc;
    font-size: 13px;
    spacing: 8px;
}}

QPushButton {{
    font-size: 13px;
    font-weight: 600;
    padding: 8px 20px;
    border-radius: 6px;
    font-family: "{font_family}";
}}

QPushButton#SaveKeyBtn {{
    background-color: #0b663b;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 7px 16px;
    border-radius: 6px;
    border: none;
}}

QPushButton#SaveKeyBtn:hover {{
    background-color: #059669;
}}

QPushButton#SaveBtn {{
    background-color: #0b663b;
    color: #ffffff;
    border: none;
}}

QPushButton#SaveBtn:hover {{
    background-color: #059669;
}}

QPushButton#CancelBtn {{
    background-color: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
}}

QPushButton#CancelBtn:hover {{
    background-color: #334155;
    color: #f8fafc;
}}
"""
    else:
        return f"""
QDialog {{
    background-color: #ffffff;
    color: #0f172a;
    font-family: "{font_family}";
}}

QGroupBox {{
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
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: #0b663b;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    font-weight: 600;
}}

QLabel {{
    color: #334155;
    font-size: 13px;
    font-weight: 500;
}}

QLineEdit {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1.5px solid #0b663b;
}}

QComboBox {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}}

QComboBox:focus {{
    border: 1.5px solid #0b663b;
}}

QComboBox QAbstractItemView {{
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: #0b663b;
    selection-color: #ffffff;
    border: 1px solid #cbd5e1;
}}

QCheckBox {{
    color: #1e293b;
    font-size: 13px;
    spacing: 8px;
}}

QPushButton {{
    font-size: 13px;
    font-weight: 600;
    padding: 8px 20px;
    border-radius: 6px;
    font-family: "{font_family}";
}}

QPushButton#SaveKeyBtn {{
    background-color: #0b663b;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 7px 16px;
    border-radius: 6px;
    border: none;
}}

QPushButton#SaveKeyBtn:hover {{
    background-color: #08502e;
}}

QPushButton#SaveBtn {{
    background-color: #0b663b;
    color: #ffffff;
    border: none;
}}

QPushButton#SaveBtn:hover {{
    background-color: #08502e;
}}

QPushButton#CancelBtn {{
    background-color: #ffffff;
    color: #475569;
    border: 1px solid #cbd5e1;
}}

QPushButton#CancelBtn:hover {{
    background-color: #f1f5f9;
}}
"""


def get_about_stylesheet(effective_theme: str = "light", font_family: str = BANGLA_FONT) -> str:
    """Return About Dialog stylesheet for effective theme."""
    if effective_theme == "dark":
        return f"""
QDialog {{
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "{font_family}";
}}
QLabel#AppTitle {{
    font-size: 18px;
    font-weight: bold;
    color: #34d399;
}}
QLabel#VersionBadge {{
    background-color: #064e3b;
    color: #6ee7b7;
    border: 1px solid #047857;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QFrame#InfoCard {{
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 14px;
}}
QLabel.InfoLabel {{
    color: #cbd5e1;
    font-size: 13px;
    line-height: 1.5;
}}
QLabel.FieldTitle {{
    font-weight: bold;
    color: #f8fafc;
    font-size: 13px;
}}
QPushButton#LinkBtn {{
    color: #34d399;
    font-weight: 600;
    font-size: 13px;
    text-decoration: underline;
    background: transparent;
    border: none;
    text-align: left;
    padding: 0;
}}
QPushButton#LinkBtn:hover {{
    color: #6ee7b7;
}}
QPushButton#CloseBtn {{
    background-color: #0b663b;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 24px;
    border-radius: 6px;
    border: none;
}}
QPushButton#CloseBtn:hover {{
    background-color: #059669;
}}
"""
    else:
        return f"""
QDialog {{
    background-color: #ffffff;
    color: #0f172a;
    font-family: "{font_family}";
}}
QLabel#AppTitle {{
    font-size: 18px;
    font-weight: bold;
    color: #0b663b;
}}
QLabel#VersionBadge {{
    background-color: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QFrame#InfoCard {{
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px;
}}
QLabel.InfoLabel {{
    color: #334155;
    font-size: 13px;
    line-height: 1.5;
}}
QLabel.FieldTitle {{
    font-weight: bold;
    color: #0f172a;
    font-size: 13px;
}}
QPushButton#LinkBtn {{
    color: #0b663b;
    font-weight: 600;
    font-size: 13px;
    text-decoration: underline;
    background: transparent;
    border: none;
    text-align: left;
    padding: 0;
}}
QPushButton#LinkBtn:hover {{
    color: #047857;
}}
QPushButton#CloseBtn {{
    background-color: #0b663b;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 24px;
    border-radius: 6px;
    border: none;
}}
QPushButton#CloseBtn:hover {{
    background-color: #08502e;
}}
"""


def get_guide_stylesheet(effective_theme: str = "light", font_family: str = BANGLA_FONT) -> str:
    """Return API Guide Dialog stylesheet for effective theme."""
    if effective_theme == "dark":
        return f"""
QDialog {{
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "{font_family}";
}}
QFrame#HeaderFrame {{
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    padding-bottom: 6px;
}}
QLabel#DialogTitle {{
    font-size: 17px;
    font-weight: bold;
    color: #34d399;
    background: transparent;
}}
QLabel#DialogSubtitle {{
    font-size: 13px;
    color: #94a3b8;
    background: transparent;
}}
QFrame#StepsFrame {{
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 14px;
}}
QLabel.StepLabel {{
    color: #f8fafc;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}}
QFrame#NoteBanner {{
    background-color: #064e3b;
    border: 1px solid #047857;
    border-radius: 6px;
    padding: 8px 12px;
}}
QLabel#NoteText {{
    color: #6ee7b7;
    font-size: 12.5px;
    font-weight: 500;
    background: transparent;
}}
QPushButton#OpenStudioBtn {{
    background-color: #0b663b;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 18px;
    border-radius: 6px;
    border: none;
}}
QPushButton#OpenStudioBtn:hover {{
    background-color: #059669;
}}
QPushButton#CloseBtn {{
    background-color: #1e293b;
    color: #e2e8f0;
    font-weight: 600;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 6px;
    border: 1px solid #334155;
}}
QPushButton#CloseBtn:hover {{
    background-color: #334155;
}}
"""
    else:
        return f"""
QDialog {{
    background-color: #ffffff;
    color: #0f172a;
    font-family: "{font_family}";
}}
QFrame#HeaderFrame {{
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 6px;
}}
QLabel#DialogTitle {{
    font-size: 17px;
    font-weight: bold;
    color: #0b663b;
    background: transparent;
}}
QLabel#DialogSubtitle {{
    font-size: 13px;
    color: #475569;
    background: transparent;
}}
QFrame#StepsFrame {{
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 14px;
}}
QLabel.StepLabel {{
    color: #0f172a;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}}
QFrame#NoteBanner {{
    background-color: #ecfdf5;
    border: 1px solid #a7f3d0;
    border-radius: 6px;
    padding: 8px 12px;
}}
QLabel#NoteText {{
    color: #065f46;
    font-size: 12.5px;
    font-weight: 500;
    background: transparent;
}}
QPushButton#OpenStudioBtn {{
    background-color: #0b663b;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 18px;
    border-radius: 6px;
    border: none;
}}
QPushButton#OpenStudioBtn:hover {{
    background-color: #08502e;
}}
QPushButton#CloseBtn {{
    background-color: #f1f5f9;
    color: #334155;
    font-weight: 600;
    font-size: 13px;
    padding: 8px 20px;
    border-radius: 6px;
    border: 1px solid #cbd5e1;
}}
QPushButton#CloseBtn:hover {{
    background-color: #e2e8f0;
}}
"""


def get_diff_spans(is_dark: bool = False) -> Dict[str, str]:
    """Return HTML inline styling for diff deletions and insertions."""
    if is_dark:
        return {
            "del_style": 'background-color: #450a0a; color: #fca5a5; font-weight: bold; border-radius: 4px; padding: 1px 4px; border: 1px solid #7f1d1d;',
            "del_inline_style": 'background-color: #450a0a; color: #fca5a5; text-decoration: line-through; border-radius: 4px; padding: 1px 4px; border: 1px solid #7f1d1d;',
            "ins_style": 'background-color: #064e3b; color: #86efac; font-weight: bold; border-radius: 4px; padding: 1px 4px; border: 1px solid #065f46;'
        }
    else:
        return {
            "del_style": 'background-color: #fee2e2; color: #991b1b; font-weight: bold; border-radius: 4px; padding: 1px 4px;',
            "del_inline_style": 'background-color: #fee2e2; color: #991b1b; text-decoration: line-through; border-radius: 4px; padding: 1px 4px;',
            "ins_style": 'background-color: #dcfce7; color: #166534; font-weight: bold; border-radius: 4px; padding: 1px 4px;'
        }


def get_messagebox_stylesheet(effective_theme: str = "light", font_family: str = BANGLA_FONT) -> str:
    """Return explicit QSS stylesheet for QMessageBox so text and background always have high contrast."""
    if effective_theme == "dark":
        return f"""
QMessageBox {{
    background-color: #1e293b;
    color: #f8fafc;
    font-family: "{font_family}";
}}
QMessageBox QLabel {{
    background-color: transparent;
    color: #f8fafc;
    font-size: 13.5px;
    font-weight: 500;
    font-family: "{font_family}";
}}
QMessageBox QPushButton {{
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 20px;
    min-width: 72px;
    font-size: 13px;
    font-weight: 600;
    font-family: "{font_family}";
}}
QMessageBox QPushButton:hover {{
    background-color: #0b663b;
    color: #ffffff;
    border-color: #10b981;
}}
"""
    else:
        return f"""
QMessageBox {{
    background-color: #ffffff;
    color: #0f172a;
    font-family: "{font_family}";
}}
QMessageBox QLabel {{
    background-color: transparent;
    color: #0f172a;
    font-size: 13.5px;
    font-weight: 500;
    font-family: "{font_family}";
}}
QMessageBox QPushButton {{
    background-color: #f1f5f9;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 20px;
    min-width: 72px;
    font-size: 13px;
    font-weight: 600;
    font-family: "{font_family}";
}}
QMessageBox QPushButton:hover {{
    background-color: #0b663b;
    color: #ffffff;
    border-color: #0b663b;
}}
"""


def apply_win32_titlebar_theme(widget: Any, effective_theme: str = "light") -> None:
    """
    Sync Qt colorScheme and Windows 11 DWM title bar dark/light mode with effective_theme
    so Light Mode never renders a black title bar or black dialog window on dark Windows OS.
    """
    is_dark = (effective_theme == "dark")
    try:
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QGuiApplication
        except ImportError:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QGuiApplication

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "setColorScheme"):
            hints.setColorScheme(Qt.ColorScheme.Dark if is_dark else Qt.ColorScheme.Light)
    except Exception:
        pass

    if sys.platform.startswith("win") and widget is not None:
        try:
            import ctypes
            hwnd = int(widget.winId())
            val = ctypes.c_int(1 if is_dark else 0)
            # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (Win11 / Win10 20H1+), 19 = older Win10
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(val), ctypes.sizeof(val)
            )
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 19, ctypes.byref(val), ctypes.sizeof(val)
            )
        except Exception:
            pass


def show_themed_message_box(
    parent: Any,
    kind: str,
    title: str,
    text: str,
    effective_theme: str = "light",
) -> int:
    """
    Display a properly themed QMessageBox ('question', 'warning', 'critical', 'information')
    whose background, text color, buttons, and Windows title bar strictly match effective_theme.
    """
    try:
        from PyQt6.QtWidgets import QMessageBox
    except ImportError:
        from PySide6.QtWidgets import QMessageBox

    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)

    if kind == "question":
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
    elif kind == "warning":
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    elif kind == "critical":
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    else:
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

    if parent is not None and hasattr(parent, "windowIcon") and not parent.windowIcon().isNull():
        msg_box.setWindowIcon(parent.windowIcon())

    msg_box.setStyleSheet(get_messagebox_stylesheet(effective_theme, BANGLA_FONT))
    apply_win32_titlebar_theme(msg_box, effective_theme)
    return msg_box.exec()

