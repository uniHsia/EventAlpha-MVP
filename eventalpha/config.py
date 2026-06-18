"""Project configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "eventalpha_mvp.sqlite3"
DEFAULT_RULES_DIR = PROJECT_ROOT / "eventalpha" / "rules"


def get_db_path() -> Path:
    """Return the configured SQLite database path."""
    return Path(os.getenv("EVENTALPHA_DB_PATH", str(DEFAULT_DB_PATH))).resolve()


def get_rules_dir() -> Path:
    """Return the configured rules directory."""
    return Path(os.getenv("EVENTALPHA_RULES_DIR", str(DEFAULT_RULES_DIR))).resolve()
