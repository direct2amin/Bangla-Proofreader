"""Bangladesh Geographical Gazetteer for context-aware Thana/Upazila, Union, Post Office, and Village verification."""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import unicodedata
from typing import Dict, Any, Optional

from app.core.assets import get_asset_path

logger = logging.getLogger(__name__)

_GAZETTEER_CACHE: Optional[Dict[str, Any]] = None


def _load_gazetteer() -> Dict[str, Any]:
    """Load the embedded Bangladesh locations database (Districts, Thanas, Unions, Post Offices, Villages)."""
    global _GAZETTEER_CACHE
    if _GAZETTEER_CACHE is not None:
        return _GAZETTEER_CACHE

    candidates = [
        get_asset_path("bd_locations.json"),
        os.path.join(os.path.dirname(__file__), "..", "assets", "bd_locations.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "bd_locations.json"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _GAZETTEER_CACHE = json.load(f)
                    return _GAZETTEER_CACHE
            except Exception as e:
                logger.debug("Failed loading bd_locations.json from %s: %s", path, e)

    _GAZETTEER_CACHE = {"districts": [], "thanas": {}}
    return _GAZETTEER_CACHE


def get_geo_reference_for_text(text: str) -> str:
    """Return a concise official gazetteer reference block if any Bangladesh Thana/Upazila is detected in text."""
    if not text or len(text) > 4000:
        return ""

    data = _load_gazetteer()
    thanas: Dict[str, Dict[str, Any]] = data.get("thanas", {})
    if not thanas:
        return ""

    norm_text = unicodedata.normalize("NFC", text)
    matched_thanas: list[str] = []

    # 1. Direct substring match for known Thana/Upazila names
    for thana_name in thanas:
        if len(thana_name) >= 3 and thana_name in norm_text:
            matched_thanas.append(thana_name)

    # 2. If 'থানা' or 'উপজেলা' is in text, also check fuzzy match on the adjacent word
    if not matched_thanas and ("থানা" in norm_text or "উপজেলা" in norm_text):
        words = re.findall(r'[\u0980-\u09FF]{3,}', norm_text)
        thana_keys = list(thanas.keys())
        for w in words:
            if w in ("থানা", "থানার", "থানায়", "উপজেলা", "উপজেলার", "উপজেলায়", "জেলা", "জেলার", "গ্রাম", "গ্রামে", "ডাকঘর", "পোস্ট"):
                continue
            close = difflib.get_close_matches(w, thana_keys, n=1, cutoff=0.82)
            if close and close[0] not in matched_thanas:
                matched_thanas.append(close[0])

    if not matched_thanas:
        return ""

    ref_lines = []
    for th in matched_thanas[:3]:
        info = thanas[th]
        dist = info.get("district", "")
        unions = info.get("unions", [])
        posts = info.get("post_offices", [])
        villages = info.get("villages", [])
        parts = [f"থানা/উপজেলা: {th}" + (f" (জেলা: {dist})" if dist else "")]
        if unions:
            parts.append("ইউনিয়নসমূহ: " + ", ".join(unions))
        if posts:
            parts.append("ডাকঘর/পোস্ট অফিস: " + ", ".join(posts))
        if villages:
            parts.append("উল্লেখযোগ্য গ্রাম: " + ", ".join(villages))
        ref_lines.append(" | ".join(parts))

    if not ref_lines:
        return ""

    return "\n<geo_reference>\n" + "\n".join(ref_lines) + "\n</geo_reference>"
