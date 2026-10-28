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
HOTKEY_ID_MAIN = 0xB001
HOTKEY_ID_QUICK_CONVERT = 0xB002


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
    Supports both the primary Proofreader hotkey and an instant Quick Convert hotkey (Ctrl+Alt+C).
    """

    def __init__(self, default_shortcut: str = "ctrl+alt+b"):
        self.current_shortcut = default_shortcut
        self.quick_convert_shortcut: Optional[str] = "ctrl+alt+c"
        self.callback: Optional[Callable[[], None]] = None
        self.quick_convert_callback: Optional[Callable[[], None]] = None
        self._is_registered = False
        self._is_paused = False
        self._win32_thread: Optional[threading.Thread] = None
        self._win32_thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._win32_success = False
        self._using_keyboard_fallback = False
        self._last_trigger_time = 0.0
        self._last_quick_trigger_time = 0.0

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def pause(self) -> None:
        """Pause triggering hotkeys without unregistering."""
        self._is_paused = True
        logger.info("Global shortcuts paused.")

    def resume(self) -> None:
        """Resume triggering hotkeys."""
        self._is_paused = False
        logger.info("Global shortcuts resumed.")

    def toggle_pause(self) -> bool:
        """Toggle pause state and return new paused state."""
        self._is_paused = not self._is_paused
        logger.info("Global shortcuts pause state toggled to: %s", self._is_paused)
        return self._is_paused

    def _handle_trigger(self, hotkey_id: int) -> None:
        """Internal callback dispatcher with debouncing and pause check."""
        if self._is_paused:
            return
        now = time.monotonic()
        if hotkey_id == HOTKEY_ID_MAIN:
            if now - self._last_trigger_time < 0.25:
                return
            self._last_trigger_time = now
            if self.callback:
                try:
                    self.callback()
                except Exception as e:
                    logger.error("Error in main shortcut callback: %s", e)
        elif hotkey_id == HOTKEY_ID_QUICK_CONVERT:
            if now - self._last_quick_trigger_time < 0.25:
                return
            self._last_quick_trigger_time = now
            if self.quick_convert_callback:
                try:
                    self.quick_convert_callback()
                except Exception as e:
                    logger.error("Error in quick convert callback: %s", e)

    def _wrapper(self) -> None:
        """Fallback callback for main shortcut."""
        self._handle_trigger(HOTKEY_ID_MAIN)

    def _win32_hotkey_loop(self, specs: List[Tuple[int, int, int]]) -> None:
        """Dedicated Win32 thread that registers the OS hotkeys and pumps WM_HOTKEY."""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._win32_thread_id = kernel32.GetCurrentThreadId()

        # Force message queue creation before RegisterHotKey
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        registered_ids: List[int] = []
        for h_id, mods, vk in specs:
            registered = bool(user32.RegisterHotKey(None, h_id, mods | MOD_NOREPEAT, vk))
            if not registered:
                # Try without MOD_NOREPEAT on older Windows builds
                registered = bool(user32.RegisterHotKey(None, h_id, mods, vk))
            if registered:
                registered_ids.append(h_id)

        self._win32_success = len(registered_ids) > 0
        self._ready_event.set()

        if not registered_ids:
            return

        try:
            while not self._stop_event.is_set():
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0 or msg.message == WM_QUIT:
                    break
                if msg.message == WM_HOTKEY:
                    self._handle_trigger(msg.wParam)
        finally:
            for h_id in registered_ids:
                try:
                    user32.UnregisterHotKey(None, h_id)
                except Exception:
                    pass

    def register(
        self,
        shortcut: str,
        callback: Callable[[], None],
        quick_convert_shortcut: Optional[str] = None,
        quick_convert_callback: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Register global keyboard shortcuts with callbacks."""
        self.unregister()
        self.current_shortcut = shortcut
        self.callback = callback
        self.quick_convert_shortcut = quick_convert_shortcut
        self.quick_convert_callback = quick_convert_callback

        specs: List[Tuple[int, int, int]] = []
        if sys.platform.startswith("win"):
            mods_main, vk_main = parse_win32_shortcut(shortcut)
            if mods_main and vk_main:
                specs.append((HOTKEY_ID_MAIN, mods_main, vk_main))

            if quick_convert_shortcut and quick_convert_callback:
                mods_qc, vk_qc = parse_win32_shortcut(quick_convert_shortcut)
                if mods_qc and vk_qc:
                    specs.append((HOTKEY_ID_QUICK_CONVERT, mods_qc, vk_qc))

            if specs:
                self._stop_event.clear()
                self._ready_event.clear()
                self._win32_success = False
                self._win32_thread = threading.Thread(
                    target=self._win32_hotkey_loop,
                    args=(specs,),
                    daemon=True,
                    name="Win32HotkeyThread",
                )
                self._win32_thread.start()
                self._ready_event.wait(timeout=1.5)

                if self._win32_success:
                    self._is_registered = True
                    self._using_keyboard_fallback = False
                    logger.info("Registered native Win32 global shortcut(s): %s", specs)
                    return True
                else:
                    logger.warning(
                        "Native Win32 RegisterHotKey could not bind shortcuts, falling back to keyboard hook."
                    )

        # Fallback to keyboard library if Win32 RegisterHotKey was unavailable
        try:
            if shortcut:
                keyboard.add_hotkey(shortcut, lambda: self._handle_trigger(HOTKEY_ID_MAIN))
            if quick_convert_shortcut and quick_convert_callback:
                keyboard.add_hotkey(quick_convert_shortcut, lambda: self._handle_trigger(HOTKEY_ID_QUICK_CONVERT))
            self._is_registered = True
            self._using_keyboard_fallback = True
            logger.info("Registered global shortcut(s) via keyboard hook: %s, %s", shortcut, quick_convert_shortcut)
            return True
        except Exception as e:
            logger.error("Failed to register shortcut: %s", e)
            return False

    def unregister(self) -> None:
        """Unregister currently active global shortcuts."""
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
                if self.current_shortcut:
                    keyboard.remove_hotkey(self.current_shortcut)
            except Exception as e:
                logger.debug("Failed unregistering keyboard fallback shortcut: %s", e)
            try:
                if self.quick_convert_shortcut:
                    keyboard.remove_hotkey(self.quick_convert_shortcut)
            except Exception as e:
                logger.debug("Failed unregistering quick convert fallback shortcut: %s", e)

        self._win32_thread = None
        self._win32_thread_id = None
        self._using_keyboard_fallback = False
        self._is_registered = False
