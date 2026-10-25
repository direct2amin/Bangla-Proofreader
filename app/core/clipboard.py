"""Windows Clipboard capture and active window text injection utility optimized for Adobe apps."""

from __future__ import annotations

import logging
import re
import time
import pyperclip
import ctypes

logger = logging.getLogger(__name__)

# Windows virtual key codes
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_MENU = 0x12  # Alt key
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_SHIFT = 0x10
VK_B = 0x42
VK_C = 0x43
VK_V = 0x56
VK_X = 0x58
VK_Z = 0x5A
KEYEVENTF_KEYUP = 0x0002


def release_modifier_keys() -> None:
    """Release only those hotkey keys/modifiers that are currently held down."""
    user32 = ctypes.windll.user32
    for vk in (VK_B, VK_Z, VK_X, VK_C, VK_LMENU, VK_RMENU, VK_MENU, VK_LCONTROL, VK_RCONTROL, VK_CONTROL):
        if user32.GetAsyncKeyState(vk) & 0x8000:
            scan = user32.MapVirtualKeyW(vk, 0)
            user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)


def send_atomic_ctrl_key(vk_key: int, release_alt: bool = False) -> None:
    """
    Send a clean Ctrl + Key sequence with hardware scan codes and realistic key timing
    so Adobe Illustrator / Photoshop / InDesign register a single atomic shortcut.
    """
    user32 = ctypes.windll.user32

    if release_alt and (user32.GetAsyncKeyState(VK_MENU) & 0x8000):
        scan_alt = user32.MapVirtualKeyW(VK_MENU, 0)
        user32.keybd_event(VK_MENU, scan_alt, KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)

    scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
    scan_key = user32.MapVirtualKeyW(vk_key, 0)

    # Press Ctrl, wait briefly for target app message loop to register Ctrl state, then press Key
    user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
    time.sleep(0.015)
    user32.keybd_event(vk_key, scan_key, 0, 0)
    time.sleep(0.015)
    user32.keybd_event(vk_key, scan_key, KEYEVENTF_KEYUP, 0)
    time.sleep(0.01)
    user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)


class ClipboardManager:
    """Handles reading from and writing to Windows system clipboard, plus atomic text injection."""

    _last_target_hwnd: int = 0

    @staticmethod
    def get_text() -> str:
        """Get current text content from the clipboard."""
        try:
            return pyperclip.paste() or ""
        except Exception as e:
            logger.error("Failed to read clipboard: %s", e)
            return ""

    @staticmethod
    def set_text(text: str) -> None:
        """Copy text to clipboard cleanly with standard Windows CRLF line endings."""
        try:
            # Normalize bare LF to standard Windows CRLF so Adobe Illustrator treats paragraphs cleanly
            normalized = re.sub(r"\r?\n", "\r\n", text) if text else ""
            pyperclip.copy(normalized)
        except Exception as e:
            logger.error("Failed to write to clipboard: %s", e)

    @classmethod
    def capture_selected_text(cls) -> str:
        """Capture selected text from Adobe (Illustrator, Photoshop, InDesign) or any standard text field.

        Uses Win32 GetClipboardSequenceNumber polling to return immediately as soon as the
        target application populates the clipboard, avoiding fixed sleep delays and avoiding
        reading heavy delayed-rendered Adobe clipboard objects before Ctrl+C.
        """
        user32 = ctypes.windll.user32
        try:
            # Record active target window handle (e.g. Adobe Illustrator) before switching focus
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd:
                cls._last_target_hwnd = int(fg_hwnd)

            # 1. Wait briefly (up to 120ms) for physical Alt key release or release held hotkey modifiers
            wait_deadline = time.perf_counter() + 0.12
            while time.perf_counter() < wait_deadline:
                if not (user32.GetAsyncKeyState(VK_MENU) & 0x8000):
                    break
                time.sleep(0.015)
            release_modifier_keys()
            time.sleep(0.015)

            # 2. Record clipboard sequence number without opening clipboard (avoids delayed-render freeze)
            seq_before = user32.GetClipboardSequenceNumber()

            # 3. Simulate clean Ctrl+C using Win32 API with hardware scan codes
            send_atomic_ctrl_key(VK_C, release_alt=True)

            # 4. Poll clipboard sequence number every 12ms (up to 400ms max for heavy Adobe AI3/PDF formats)
            deadline = time.perf_counter() + 0.40
            seq_changed = False
            while time.perf_counter() < deadline:
                time.sleep(0.012)
                if user32.GetClipboardSequenceNumber() != seq_before:
                    seq_changed = True
                    break

            if seq_changed:
                # Brief 15ms grace for multi-format clipboard writers (Adobe) to finish CF_UNICODETEXT
                time.sleep(0.015)
                new_clip = cls.get_text()
                if new_clip and new_clip.strip():
                    return new_clip

            # Fallback: if the user selected the exact same text already in clipboard or app
            # required a second Ctrl+C pulse
            send_atomic_ctrl_key(VK_C, release_alt=True)
            time.sleep(0.08)
            if user32.GetClipboardSequenceNumber() != seq_before:
                new_clip = cls.get_text()
                if new_clip and new_clip.strip():
                    return new_clip

            return ""
        except Exception as e:
            logger.error("Failed to capture selected text: %s", e)
            return ""

    @classmethod
    def paste_into_active_window(cls, text: str, set_clipboard: bool = False) -> None:
        """Perform a single atomic replacement paste (Ctrl+V) into active Adobe / text window.

        Specifically designed for Adobe Illustrator single-step Undo (Ctrl+Z):
        - The clipboard MUST be populated BEFORE minimizing DiffWindow so that when
          Adobe Illustrator receives WM_ACTIVATEAPP, it pre-converts the clipboard once
          (identical to manual Copy + switch window + Ctrl+V).
        - Does NOT rewrite/empty the clipboard while Illustrator is already in the foreground.
        - Does NOT send unsolicited VK_MENU (Alt) keyup events.
        - Sends a single hardware-scanned Ctrl+V so Illustrator registers 1 single Undo step.
        """
        try:
            if set_clipboard and text:
                cls.set_text(text)
                time.sleep(0.05)

            # Send single clean Ctrl+V (without fake Alt keyup)
            send_atomic_ctrl_key(VK_V, release_alt=False)
            logger.info("Atomic paste (Ctrl+V) completed successfully.")
        except Exception as e:
            logger.error("Failed to paste into active window: %s", e)
