"""Main entry point for Bangla Proofreader with System Tray and Global Shortcut integration."""

from __future__ import annotations

import logging
import sys
import os
from typing import Optional

# Ensure parent directory is in sys.path when launched directly as a script (e.g. from Windows Run registry)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal as Signal, QObject, QThread
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QFontDatabase
    from PyQt6.QtWidgets import (
        QApplication, QSystemTrayIcon, QMenu, QWidget
    )
except ImportError:
    from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QFontDatabase
    from PySide6.QtWidgets import (
        QApplication, QSystemTrayIcon, QMenu, QWidget
    )

from app.core.engine_manager import EngineManager
from app.core.clipboard import ClipboardManager
from app.core.config import load_config
from app.core.shortcuts import ShortcutManager
from app.ui.diff_window import DiffWindow
from app.ui.settings_dialog import SettingsDialog
from app.utils.i18n import t
from app.core.assets import get_asset_path

LOGO_ICO_PATH = get_asset_path("logo.ico")
LOGO_ICON_PATH = get_asset_path("logo_icon.png")
TRAY_ICON_PATH = get_asset_path("tray_icon.png")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("BanglaProofreader")


def load_custom_bangla_font() -> str:
    """Load Bornomala font dynamically at startup and return font family name."""
    base_dir = os.path.dirname(__file__)
    candidate_paths = [
        os.path.join(base_dir, "assets", "fonts", "Bornomala-Trio-Regular.ttf"),
        os.path.join(base_dir, "assets", "Bornomala-Trio-Regular.ttf"),
        os.path.join(base_dir, "..", "assets", "fonts", "Bornomala-Trio-Regular.ttf"),
        os.path.join(base_dir, "..", "assets", "Bornomala-Trio-Regular.ttf"),
    ]

    for path in candidate_paths:
        if os.path.exists(path):
            font_id = QFontDatabase.addApplicationFont(path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    logger.info("Successfully loaded embedded font: '%s' from %s", families[0], path)
                    return families[0]

    logger.warning("Bornomala font file not found or failed to load. Falling back to Nirmala UI.")
    return "Nirmala UI"


def force_activate_window(window: QWidget) -> None:
    """Forcefully bring the Qt window to the foreground on Windows without blocking on target thread."""
    if window.isMinimized():
        window.showNormal()
    else:
        window.show()

    try:
        import ctypes
        user32 = ctypes.windll.user32

        hwnd = int(window.winId())

        # Un-minimize if minimized
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE

        # Bypass Windows Foreground Lock via brief TOPMOST promotion + Alt keyup
        # (Avoids AttachThreadInput which blocks when Adobe apps are busy rendering clipboard data)
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2

        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        user32.keybd_event(0x12, 0, 0x0002, 0)  # VK_MENU keyup satisfies foreground lock
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    except Exception as e:
        logger.debug("Win32 force activate error: %s", e)

    window.raise_()
    window.activateWindow()


def create_tray_icon() -> QIcon:
    """Load the custom checkmark tray icon or fall back to logo/fallback."""
    if os.path.exists(TRAY_ICON_PATH):
        return QIcon(TRAY_ICON_PATH)
    if os.path.exists(LOGO_ICON_PATH):
        return QIcon(LOGO_ICON_PATH)

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor("#0b663b"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 16, 16)

    painter.setPen(QColor("#ffffff"))
    font = QFont("Nirmala UI", 30, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "আ")
    painter.end()

    return QIcon(pixmap)


class HotkeyBridge(QObject):
    """Thread-safe bridge to deliver global hotkey triggers to the Qt event loop."""
    hotkey_pressed = Signal()
    quick_convert_pressed = Signal()


class CaptureWorker(QThread):
    """Dedicated background worker thread to capture text from Adobe/active apps without UI freeze."""
    text_captured = Signal(str)
    no_text_selected = Signal()

    def run(self):
        try:
            captured_text = ClipboardManager.capture_selected_text()
            if captured_text and captured_text.strip():
                self.text_captured.emit(captured_text.strip())
            else:
                self.no_text_selected.emit()
        except Exception as e:
            logger.error("Error in CaptureWorker: %s", e)
            self.no_text_selected.emit()


class QuickConvertWorker(QThread):
    """Dedicated background worker to capture Bijoy text, convert to Unicode offline, and replace in active app with NO window."""
    conversion_finished = Signal(bool, int)

    def run(self):
        try:
            logger.info("QuickConvertWorker: Capturing text from active application...")
            captured = ClipboardManager.capture_selected_text()
            if not captured or not captured.strip():
                logger.info("QuickConvertWorker: No text selected.")
                self.conversion_finished.emit(False, 0)
                return

            logger.info("QuickConvertWorker: Captured %d characters. Converting Bijoy to Unicode offline...", len(captured))
            from app.utils.bijoy_converter import convert_bijoy_to_unicode
            unicode_text = convert_bijoy_to_unicode(captured)

            logger.info("QuickConvertWorker: Injecting converted text into active application...")
            ClipboardManager.paste_into_active_window(unicode_text, set_clipboard=True)
            self.conversion_finished.emit(True, len(unicode_text))
        except Exception as e:
            logger.error("Error in QuickConvertWorker: %s", e)
            self.conversion_finished.emit(False, 0)


class BanglaProofreaderApp:
    """Core Application Coordinator."""

    def __init__(self):
        self.engine_manager = EngineManager()
        self.diff_window = DiffWindow(engine_manager=self.engine_manager)
        saved_shortcut = (load_config().get("shortcut", "ctrl+alt+b") or "ctrl+alt+b").strip().lower()
        if saved_shortcut not in ("ctrl+alt+b", "ctrl+alt+z", "ctrl+alt+x"):
            saved_shortcut = "ctrl+alt+b"
        self.shortcut_manager = ShortcutManager(default_shortcut=saved_shortcut)
        self.bridge = HotkeyBridge()
        self.bridge.hotkey_pressed.connect(self.on_hotkey_triggered)
        self.bridge.quick_convert_pressed.connect(self.on_quick_convert_triggered)
        self.diff_window.shortcut_changed.connect(self.update_shortcut)
        self.capture_worker: Optional[CaptureWorker] = None
        self.quick_convert_worker: Optional[QuickConvertWorker] = None

        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.init_tray()
        self.init_shortcuts()

    def init_tray(self):
        """Initialize the Windows system tray icon and context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not supported on this platform.")
            return

        icon = create_tray_icon()
        self.tray_icon = QSystemTrayIcon(icon, self.diff_window)
        self.tray_icon.setToolTip("Bangla Proofreader")

        tray_menu = QMenu()

        self.restore_action = tray_menu.addAction("Open / Restore")
        self.restore_action.triggered.connect(self.show_window)

        self.pause_hotkey_action = tray_menu.addAction("Pause Hotkey")
        self.pause_hotkey_action.triggered.connect(self.toggle_hotkey_pause)

        settings_action = tray_menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings_dialog)

        about_action = tray_menu.addAction("About")
        about_action.triggered.connect(self.diff_window.open_about_dialog)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            self.show_window()

    def toggle_hotkey_pause(self):
        """Toggle pause state of global shortcut listener."""
        is_paused = self.shortcut_manager.toggle_pause()
        sc_display = "+".join(part.capitalize() for part in self.shortcut_manager.current_shortcut.split("+"))
        if is_paused:
            self.pause_hotkey_action.setText("Resume Hotkey")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "Bangla Proofreader",
                    f"Global shortcut ({sc_display}) paused.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            self.pause_hotkey_action.setText("Pause Hotkey")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "Bangla Proofreader",
                    f"Global shortcut ({sc_display}) resumed.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )

    def open_settings_dialog(self):
        """Open settings dialog from system tray."""
        self.diff_window.open_settings_dialog()

    def init_shortcuts(self):
        """Register system-wide global hotkeys."""
        self.update_shortcut(self.shortcut_manager.current_shortcut)

    def update_shortcut(self, shortcut: Optional[str] = None):
        """Register or update global shortcuts dynamically."""
        cfg = load_config()
        sc = (shortcut or cfg.get("shortcut", "ctrl+alt+b") or "ctrl+alt+b").strip().lower()
        if sc not in ("ctrl+alt+b", "ctrl+alt+z", "ctrl+alt+x"):
            sc = "ctrl+alt+b"

        quick_enabled = cfg.get("quick_convert_enabled", True)
        quick_sc = "ctrl+alt+c" if quick_enabled else None

        def trigger_main():
            self.bridge.hotkey_pressed.emit()

        def trigger_quick():
            self.bridge.quick_convert_pressed.emit()

        success = self.shortcut_manager.register(
            shortcut=sc,
            callback=trigger_main,
            quick_convert_shortcut=quick_sc,
            quick_convert_callback=trigger_quick if quick_sc else None,
        )
        if success:
            logger.info("Global shortcuts registered: main=%s, quick_convert=%s", sc, quick_sc)
        else:
            logger.warning("Could not register one or more global shortcuts.")

    def on_quick_convert_triggered(self):
        """Called when Ctrl+Alt+C is pressed anywhere in Windows (Quick Unicode Convert without window)."""
        logger.info("Quick convert shortcut (Ctrl+Alt+C) triggered. Launching QuickConvertWorker...")
        if self.quick_convert_worker and self.quick_convert_worker.isRunning():
            logger.info("Quick convert worker is already running. Ignoring duplicate trigger.")
            return

        self.quick_convert_worker = QuickConvertWorker()
        self.quick_convert_worker.conversion_finished.connect(self.on_quick_convert_finished)
        self.quick_convert_worker.start()

    def on_quick_convert_finished(self, success: bool, char_count: int):
        if success:
            logger.info("Quick convert completed: %d characters converted and replaced.", char_count)

    def on_hotkey_triggered(self):
        """Called when Ctrl+Alt+B is pressed anywhere in Windows."""
        logger.info("Global hotkey triggered. Launching background capture worker...")
        if self.capture_worker and self.capture_worker.isRunning():
            logger.info("Capture worker is already running. Ignoring overlapping hotkey.")
            return

        self.capture_worker = CaptureWorker()
        self.capture_worker.text_captured.connect(self.on_text_captured)
        self.capture_worker.no_text_selected.connect(self.on_no_text_selected)
        self.capture_worker.start()

    def on_text_captured(self, text: str):
        """Called on main UI thread when text is captured from active app."""
        logger.info("Captured %d characters from active application. Processing...", len(text))
        self.show_window()
        QApplication.processEvents()
        self.diff_window.set_input_text(text)

    def on_no_text_selected(self):
        """Called on main UI thread when no text was selected."""
        logger.info("No text was selected in the active application.")
        self.show_window()
        QApplication.processEvents()
        # Display gentle notification without clearing existing text
        sc_display = "+".join(part.capitalize() for part in self.shortcut_manager.current_shortcut.split("+"))
        self.diff_window.show_feedback(
            t("no_text_selected_warn", self.diff_window.lang).replace("Ctrl+Alt+B", sc_display)
        )

    def show_window(self):
        """Bring the diff window to focus forcefully, restoring if hidden/minimized."""
        force_activate_window(self.diff_window)

    def quit_app(self):
        self.shortcut_manager.unregister()
        QApplication.quit()


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Uncaught exception in application thread:", exc_info=(exc_type, exc_value, exc_traceback))


def main():
    # Install safety exception hook so unhandled exceptions do not unexpectedly terminate the app
    sys.excepthook = handle_uncaught_exception

    # Force Windows Taskbar to display our custom application logo instead of python icon
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("amin.banglaproofreader.desktop.1.6.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Bangla Proofreader")

    # Native Windows Bengali UI Font (Nirmala UI)
    app.setFont(QFont("Nirmala UI", 10))
    app.setQuitOnLastWindowClosed(False)

    if os.path.exists(LOGO_ICO_PATH):
        app.setWindowIcon(QIcon(LOGO_ICO_PATH))
    elif os.path.exists(LOGO_ICON_PATH):
        app.setWindowIcon(QIcon(LOGO_ICON_PATH))

    app_instance = BanglaProofreaderApp()

    # Check for silent start argument (e.g. from Windows autostart on boot)
    start_minimized = any(arg in sys.argv for arg in ("--minimized", "--tray", "-m"))
    if not start_minimized:
        app_instance.show_window()
        logger.info("Bangla Proofreader started with native font: Nirmala UI.")
    else:
        logger.info("Bangla Proofreader started silently minimized to system tray.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
