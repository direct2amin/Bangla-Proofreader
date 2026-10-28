"""Engine Manager: Supports both Offline (Local Dictionary - Instant) and Online AI (Gemini AI - Contextual) modes."""

from __future__ import annotations

import logging
import socket
import sys
from typing import Optional

from app.core.config import load_config, save_config
from app.engines.gemini_engine import GeminiProofreaderEngine
from app.utils.bijoy_converter import convert_bijoy_to_unicode, is_bijoy_text
from app.utils.offline_checker import OfflineSpellChecker

logger = logging.getLogger(__name__)


def is_internet_connected(timeout: float = 0.8) -> bool:
    """Fast check for active internet connectivity on the PC."""
    # 1. Instant Win32 WinInet adapter check on Windows
    if sys.platform.startswith("win"):
        try:
            import ctypes
            flags = ctypes.c_ulong(0)
            if ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0) == 0:
                return False
        except Exception:
            pass

    # 2. Fast non-blocking DNS socket check
    for host in ("8.8.8.8", "1.1.1.1"):
        try:
            with socket.create_connection((host, 53), timeout=timeout):
                return True
        except OSError:
            continue
    return False


class EngineManager:
    """Manages proofreading execution across Offline Local Dictionary and Online Google Gemini AI."""

    def __init__(self, check_network_on_init: bool = True):
        config = load_config()
        api_key = config.get("gemini_api_key", "")
        model_name = config.get("gemini_model", "gemini-3.5-flash")
        self.mode: str = config.get("proofread_mode", "online")
        if self.mode not in ("online", "offline"):
            self.mode = "online"
        self.auto_switched_offline: bool = False

        # If in online mode but PC has no internet connection, automatically switch to offline mode
        if check_network_on_init and self.mode == "online" and not self.is_internet_available():
            logger.info("No internet connection detected at startup. Automatically switching to Offline Mode.")
            self.set_mode("offline")
            self.auto_switched_offline = True

        self.gemini_engine = GeminiProofreaderEngine(api_key=api_key, model_name=model_name)
        self.offline_checker = OfflineSpellChecker()

    @staticmethod
    def is_internet_available() -> bool:
        """Return True if the PC currently has an active internet connection."""
        return is_internet_connected()

    def set_mode(self, mode: str) -> None:
        """Switch between 'offline' and 'online' proofreading modes and persist to config."""
        normalized = "offline" if str(mode).strip().lower() == "offline" else "online"
        self.mode = normalized
        config = load_config()
        config["proofread_mode"] = normalized
        save_config(config)

    def get_mode(self) -> str:
        """Return active proofreading mode ('offline' or 'online')."""
        return self.mode

    def set_gemini_api_key(self, api_key: str) -> None:
        """Update Gemini API key and persist to config."""
        self.gemini_engine.set_api_key(api_key)
        config = load_config()
        config["gemini_api_key"] = api_key
        save_config(config)

    def is_gemini_available(self) -> bool:
        """Check if Gemini API client is ready."""
        return self.gemini_engine.is_available()

    def proofread(self, text: str, mode: Optional[str] = None) -> str:
        """Proofread input text in the selected mode ('offline' or 'online'), automatically handling Bijoy encoding."""
        if not text or not text.strip():
            return text

        if is_bijoy_text(text):
            logger.info("Bijoy text detected in EngineManager. Auto-converting to Unicode...")
            text = convert_bijoy_to_unicode(text)

        active_mode = (mode or self.mode or "online").strip().lower()
        if active_mode == "offline":
            return self.offline_checker.proofread_text(text)

        if not self.gemini_engine.is_available():
            raise RuntimeError(
                "Gemini API Key সংযুক্ত করা নেই। অনুগ্রহ করে ওপরে আপনার API Key দিয়ে 'সেভ' বাটনে ক্লিক করুন, "
                "অথবা 'Offline (Local Dictionary- Instant)' মোড নির্বাচন করুন।"
            )

        return self.gemini_engine.proofread(text)
