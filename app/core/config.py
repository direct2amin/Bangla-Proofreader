"""Configuration manager for Bangla Proofreader with permanent %APPDATA% storage."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


def get_config_file_path() -> Path:
    """Return permanent, user-writable config.json path in %APPDATA% (survives reboots & updates)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        config_dir = Path(appdata) / "BanglaProofreader"
    else:
        config_dir = Path.home() / ".bangla_proofreader"

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    return config_dir / "config.json"


CONFIG_FILE = get_config_file_path()

DEFAULT_CONFIG: Dict[str, Any] = {
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "gemini_model": "gemini-3.5-flash-lite",
    "shortcut": "ctrl+alt+b",
    "quick_convert_enabled": True,
    "auto_paste": True,
    "ui_language": "en",
    "minimize_to_tray_on_close": True,
    "start_with_windows": False,
    "editor_font_size": 14,
    "theme": "system",
    "proofread_mode": "online",
}


CURATED_GEMINI_MODELS = [
    ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite (Ultra-fast ~0.8s - Recommended)"),
    ("gemini-flash-lite-latest", "gemini-flash-lite-latest (Auto-Updating Lite)"),
    ("gemini-3.5-flash", "gemini-3.5-flash (High Accuracy ~3s)"),
    ("gemini-flash-latest", "gemini-flash-latest (Auto-Updating Standard)"),
    ("gemini-3.1-flash-lite", "gemini-3.1-flash-lite (Lightweight Fallback)"),
]


def load_config() -> Dict[str, Any]:
    """Load settings from permanent %APPDATA% config.json or environment."""
    config = dict(DEFAULT_CONFIG)

    # 1. If permanent config doesn't exist yet, migrate from legacy/dev config.json
    if not CONFIG_FILE.exists():
        legacy_candidates = [
            Path(__file__).resolve().parent.parent.parent / "config.json",
            Path(os.getcwd()) / "config.json",
        ]
        for leg in legacy_candidates:
            if leg.exists():
                try:
                    with open(leg, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        config.update(saved)
                    save_config(config)
                    break
                except Exception:
                    pass

    # 2. Read from permanent APPDATA config.json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass

    # Automatically migrate retired legacy models (e.g. 2.5, 2.0, 1.5) to active gemini-3.5-flash-lite
    if config.get("gemini_model") in (
        "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash",
        "gemini-2.5-pro", "gemini-1.5-pro", None
    ):
        config["gemini_model"] = "gemini-3.5-flash-lite"

    # Ensure main shortcut does not clash with dedicated quick-convert shortcut (Ctrl+Alt+C)
    if config.get("shortcut", "").strip().lower() == "ctrl+alt+c":
        config["shortcut"] = "ctrl+alt+b"

    # Environment variable priority if set
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        config["gemini_api_key"] = env_key

    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save settings permanently to %APPDATA% config.json."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
