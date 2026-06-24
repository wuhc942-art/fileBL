from __future__ import annotations

import json
from pathlib import Path


SETTINGS_FILE = "app_settings.json"


def settings_path(app_root: Path) -> Path:
    return app_root / SETTINGS_FILE


def load_settings(app_root: Path) -> dict:
    path = settings_path(app_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(app_root: Path, settings: dict) -> Path:
    path = settings_path(app_root)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
