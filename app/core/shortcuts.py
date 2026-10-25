"""System-wide global shortcut manager using native Win32 RegisterHotKey with keyboard fallback."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import sys
import threading
import time
from typing import Callable, Optional, Tuple
import keyboard

logger = logging.getLogger(__name__)

# Win32 Constants for RegisterHotKey
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
HOTKEY_ID = 0xB001


def parse_win32_shortcut(shortcut: str) -> Tuple[int, int]:
    """
    Parse a shortcut string like 'ctrl+alt+b' into Win32 (modifiers, virtual_key_code).
    Returns (0, 0) if the shortcut cannot be mapped to a standard Win32 virtual key.
    """
    parts = [p.strip().lower() for p in shortcut.split("+") if p.strip()]
    modifiers = 0
    vk = 0

    for part in parts:
        if part in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif part == "alt":
            modifiers |= MOD_ALT
        elif part == "shift":
            modifiers |= MOD_SHIFT
        elif part in ("win", "windows", "super"):
            modifiers |= MOD_WIN
        elif len(part) == 1 and "a" <= part <= "z":
            vk = ord(part.upper())
        elif len(part) == 1 and "0" <= part <= "9":
            vk = ord(part)

    return modifiers, vk


class ShortcutManager:
    """
    Manages global Windows keyboard hotkeys with pause and resume capability.
    Uses native Win32 RegisterHotKey on a dedicated message-loop thread so Windows
    never silently drops the hook (unlike WH_KEYBOARD_LL in the keyboard library).
    """

    def __init__(self, default_shortcut: str = "ctrl+alt+b"):
        self.current_shortcut = default_shortcut
        self.callback: Optional[Callable[[], None]] = None
        self._is_registered = False
        self._is_paused = False
        self._win32_thread: Optional[threading.Thread] = None
        self._win32_thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._win32_success = False
        self._using_keyboard_fallback = False
        self._last_trigger_time = 0.0

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def pause(self) -> None:
        """Pause triggering hotkey without unregistering."""
        self._is_paused = True
        logger.info("Global shortcut '%s' paused.", self.current_shortcut)

    def resume(self) -> None:
        """Resume triggering hotkey."""
        self._is_paused = False
        logger.info("Global shortcut '%s' resumed.", self.current_shortcut)

    def toggle_pause(self) -> bool:
        """Toggle pause state and return new paused state."""
        self._is_paused = not self._is_paused
        logger.info("Global shortcut '%s' pause state toggled to: %s", self.current_shortcut, self._is_paused)
        return self._is_paused

    def _wrapper(self) -> None:
        """Internal callback that only executes if not paused, with 250ms debounce."""
        if self._is_paused or not self.callback:
            return
        now = time.monotonic()
        if now - self._last_trigger_time < 0.25:
            return
        self._last_trigger_time = now
        try:
            self.callback()
        except Exception as e:
            logger.error("Error in shortcut callback: %s", e)

    def _win32_hotkey_loop(self, modifiers: int, vk: int) -> None:
        """Dedicated Win32 thread that registers the OS hotkey and pumps WM_HOTKEY."""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._win32_thread_id = kernel32.GetCurrentThreadId()

        # Force message queue creation before RegisterHotKey
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        registered = bool(user32.RegisterHotKey(None, HOTKEY_ID, modifiers | MOD_NOREPEAT, vk))
        if not registered:
            # Try without MOD_NOREPEAT on older Windows builds
            registered = bool(user32.RegisterHotKey(None, HOTKEY_ID, modifiers, vk))

        self._win32_success = registered
        self._ready_event.set()

        if not registered:
            return

        try:
            while not self._stop_event.is_set():
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0 or msg.message == WM_QUIT:
                    break
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self._wrapper()
        finally:
            try:
                user32.UnregisterHotKey(None, HOTKEY_ID)
            except Exception:
                pass

    def register(self, shortcut: str, callback: Callable[[], None]) -> bool:
        """Register a global keyboard shortcut with a callback."""
        self.unregister()
        self.current_shortcut = shortcut
        self.callback = callback

        if sys.platform.startswith("win"):
            modifiers, vk = parse_win32_shortcut(shortcut)
            if modifiers and vk:
                self._stop_event.clear()
                self._ready_event.clear()
                self._win32_success = False
                self._win32_thread = threading.Thread(
                    target=self._win32_hotkey_loop,
                    args=(modifiers, vk),
                    daemon=True,
                    name="Win32HotkeyThread",
                )
                self._win32_thread.start()
                self._ready_event.wait(timeout=1.5)

                if self._win32_success:
                    self._is_registered = True
                    self._using_keyboard_fallback = False
                    logger.info("Registered native Win32 global shortcut: %s", shortcut)
                    return True
                else:
                    logger.warning(
                        "Native Win32 RegisterHotKey could not bind '%s', falling back to keyboard hook.",
                        shortcut,
                    )

        # Fallback to keyboard library if Win32 RegisterHotKey was unavailable
        try:
            keyboard.add_hotkey(shortcut, self._wrapper)
            self._is_registered = True
            self._using_keyboard_fallback = True
            logger.info("Registered global shortcut via keyboard hook: %s", shortcut)
            return True
        except Exception as e:
            logger.error("Failed to register shortcut '%s': %s", shortcut, e)
            return False

    def unregister(self) -> None:
        """Unregister currently active global shortcut."""
        if not self._is_registered:
            return

        if sys.platform.startswith("win") and self._win32_thread and self._win32_thread.is_alive():
            self._stop_event.set()
            if self._win32_thread_id:
                try:
                    ctypes.windll.user32.PostThreadMessageW(self._win32_thread_id, WM_QUIT, 0, 0)
                except Exception:
                    pass
            self._win32_thread.join(timeout=1.0)

        if self._using_keyboard_fallback:
            try:
                keyboard.remove_hotkey(self.current_shortcut)
            except Exception as e:
                logger.debug("Failed unregistering keyboard fallback shortcut: %s", e)

        self._win32_thread = None
        self._win32_thread_id = None
        self._using_keyboard_fallback = False
        self._is_registered = False
