"""Windows Autostart (Run on Boot) management via HKCU registry without Admin rights."""

from __future__ import annotations

import logging
import os
import sys
import winreg

logger = logging.getLogger(__name__)

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "BanglaProofreader"


def get_app_launch_command() -> str:
    """Return command string to launch app silently minimized at Windows startup."""
    # If compiled with PyInstaller
    if getattr(sys, "frozen", False):
        exe = sys.executable
        return f'"{exe}" --minimized'

    # Running from Python source: prefer pythonw.exe so no console window flashes
    python_exe = sys.executable
    pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
    if os.path.exists(pythonw):
        python_exe = pythonw

    main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return f'"{python_exe}" "{main_script}" --minimized'


def is_start_with_windows_enabled() -> bool:
    """Check if app is registered in HKCU Run registry key."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except (FileNotFoundError, OSError):
        return False


def set_start_with_windows(enable: bool) -> bool:
    """Register or unregister app in HKCU Run key cleanly without Admin rights."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                cmd = get_app_launch_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                logger.info("Registered BanglaProofreader in HKCU Run: %s", cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Unregistered BanglaProofreader from HKCU Run.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.error("Failed to update Windows autostart registry: %s", e)
        return False
