import json
from pathlib import Path


def load_json(file_path, default):
    try:
        file_path = Path(file_path)

        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)

    except (json.JSONDecodeError, OSError):
        pass

    return default


def save_json(file_path, data):
    file_path = Path(file_path)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )