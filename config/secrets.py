"""Configuration value resolution independent of the storage adapters."""

import os
from pathlib import Path

from .settings import ENV_FILE


def load_dotenv_file(env_file: str | Path = ENV_FILE) -> dict[str, str]:
    """Read simple ``KEY=VALUE`` pairs without requiring python-dotenv."""

    values: dict[str, str] = {}
    path = Path(env_file)
    if not path.exists():
        return values
    try:
        with path.open("r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                values[key] = value
    except OSError:
        pass
    return values


def get_secret(name: str, env_file: str | Path = ENV_FILE) -> str | None:
    """Resolve a secret from Streamlit secrets, ``.env``, then the environment."""

    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    value = load_dotenv_file(env_file).get(name)
    return value or os.getenv(name) or None
