"""Centralised, dependency-free application settings.

Keeping paths and environment names here prevents Streamlit pages and
repositories from each deriving their own configuration.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    """Filesystem and environment configuration for one application instance."""

    base_dir: Path
    data_dir: Path
    env_file: Path
    supabase_url_key: str = "SUPABASE_URL"
    supabase_key_name: str = "SUPABASE_KEY"
    gemini_api_key_name: str = "GEMINI_API_KEY"


def get_settings(base_dir: str | Path | None = None) -> AppSettings:
    """Return settings rooted at the repository/application directory."""

    root = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parent.parent
    root = root.resolve()
    return AppSettings(
        base_dir=root,
        data_dir=root / "data",
        env_file=root / ".env",
    )


SETTINGS = get_settings()
BASE_DIR = SETTINGS.base_dir
DATA_DIR = SETTINGS.data_dir
ENV_FILE = SETTINGS.env_file
