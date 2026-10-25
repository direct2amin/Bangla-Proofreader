"""Engine Manager: Dedicated solely to Google Gemini AI Proofreading."""

from __future__ import annotations

import logging
from typing import Optional
from app.engines.gemini_engine import GeminiProofreaderEngine
from app.core.config import load_config, save_config

logger = logging.getLogger(__name__)


class EngineManager:
    """Manages proofreading execution exclusively via Google Gemini AI."""

    def __init__(self):
        config = load_config()
        api_key = config.get("gemini_api_key", "")
        model_name = config.get("gemini_model", "gemini-3.5-flash")
        self.gemini_engine = GeminiProofreaderEngine(api_key=api_key, model_name=model_name)

    def set_gemini_api_key(self, api_key: str) -> None:
        """Update Gemini API key and persist to config."""
        self.gemini_engine.set_api_key(api_key)
        config = load_config()
        config["gemini_api_key"] = api_key
        save_config(config)

    def is_gemini_available(self) -> bool:
        """Check if Gemini API client is ready."""
        return self.gemini_engine.is_available()

    def proofread(self, text: str) -> str:
        """Proofread input text using Google Gemini AI, automatically handling Bijoy encoding."""
        if not text.strip():
            return text

        from app.utils.bijoy_converter import is_bijoy_text, convert_bijoy_to_unicode
        if is_bijoy_text(text):
            logger.info("Bijoy text detected in EngineManager. Auto-converting to Unicode...")
            text = convert_bijoy_to_unicode(text)

        if not self.gemini_engine.is_available():
            raise RuntimeError("Gemini API Key সংযুক্ত করা নেই। অনুগ্রহ করে ওপরে আপনার API Key দিয়ে 'সেভ' বাটনে ক্লিক করুন।")

        return self.gemini_engine.proofread(text)
