"""Asset manager providing robust path resolution for both source and PyInstaller frozen builds."""

from __future__ import annotations

import os
import sys


def get_asset_path(filename: str) -> str:
    """Resolve asset path correctly in source development and PyInstaller bundled builds."""
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
        candidates = [
            os.path.join(base_dir, "_internal", "app", "assets", filename),
            os.path.join(base_dir, "_internal", "assets", filename),
            os.path.join(base_dir, "app", "assets", filename),
            os.path.join(base_dir, "assets", filename),
            os.path.join(base_dir, filename),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return candidates[0]

    # Source development mode: app/assets/
    core_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(core_dir)
    primary = os.path.join(app_dir, "assets", filename)
    if os.path.exists(primary):
        return primary

    # Fallback paths
    root_dir = os.path.dirname(app_dir)
    fallback = os.path.join(root_dir, "app", "assets", filename)
    if os.path.exists(fallback):
        return fallback

    return primary
