"""Engine Manager: Provides pure AI Proofreading (Gemini AI) and offline Bijoy-to-Unicode conversion."""

from __future__ import annotations

import logging
import socket
import sys
from typing import Optional

from app.core.config import load_config, save_config
from app.engines.gemini_engine import GeminiProofreaderEngine
from app.engines.sentence_polisher import SentencePolishResult, SentencePolisher
from app.utils.bijoy_converter import convert_bijoy_to_unicode, is_bijoy_text

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
    """Manages AI proofreading execution via Google Gemini and offline Bijoy conversion."""

    def __init__(self, check_network_on_init: bool = True):
        config = load_config()
        api_key = config.get("gemini_api_key", "")
        model_name = config.get("gemini_model", "gemini-3.5-flash-lite")
        self.mode: str = "online"

        self.gemini_engine = GeminiProofreaderEngine(api_key=api_key, model_name=model_name)
        self.sentence_polisher = SentencePolisher(api_key=api_key)

    @staticmethod
    def is_internet_available() -> bool:
        """Return True if the PC currently has an active internet connection."""
        return is_internet_connected()

    def set_mode(self, mode: str) -> None:
        """Retained for compatibility."""
        self.mode = "online"

    def get_mode(self) -> str:
        """Return active proofreading mode."""
        return "online"

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
        """Proofread input text via Gemini AI, automatically handling Bijoy encoding offline."""
        if not text or not text.strip():
            return text

        # Offline pure Bijoy-to-Unicode conversion
        if is_bijoy_text(text):
            logger.info("Bijoy text detected in EngineManager. Auto-converting to Unicode offline...")
            text = convert_bijoy_to_unicode(text)

        if not self.gemini_engine.is_available():
            raise RuntimeError(
                "Gemini API Key সংযুক্ত করা নেই। অনুগ্রহ করে ওপরে আপনার API Key দিয়ে 'সংরক্ষণ করুন' বাটনে ক্লিক করুন।"
            )

        return self.gemini_engine.proofread(text)

    def polish_sentences(self, text: str) -> SentencePolishResult:
        """Execute sentence-level stylistic polishing via Gemini AI."""
        if not text or not text.strip():
            return SentencePolishResult(original_text=text, full_polished_text=text, changes=[])

        if is_bijoy_text(text):
            text = convert_bijoy_to_unicode(text)

        if not self.gemini_engine.is_available():
            raise RuntimeError(
                "Gemini API Key সংযুক্ত করা নেই। বাক্য পরিমার্জনের জন্য অনুগ্রহ করে ওপরে আপনার API Key দিয়ে সেভ করুন।"
            )

        return self.sentence_polisher.polish_text(text)
