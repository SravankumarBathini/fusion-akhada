"""Small, filesystem-only JSON repository used by local development/fallbacks."""

import json
from pathlib import Path
from typing import Any


def load_json(file_path: str | Path, default: Any = None) -> Any:
    """Load JSON data, returning ``default`` for missing or invalid files."""

    path = Path(file_path)
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(file_path: str | Path, data: Any) -> bool:
    """Persist JSON data and report whether the write succeeded."""

    path = Path(file_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        return True
    except OSError:
        return False
