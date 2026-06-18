"""Small SQLite repository wrapper."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteRepository:
    """Owns SQLite connections and schema initialization."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.schema_path = Path(__file__).with_name("schema.sql")

    def connect(self) -> sqlite3.Connection:
        """Open a row-based SQLite connection."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        """Create all MVP tables if they do not exist."""
        with self.connect() as conn:
            conn.executescript(self.schema_path.read_text(encoding="utf-8"))
            self._apply_migrations(conn)
            conn.commit()

    def _apply_migrations(self, conn: sqlite3.Connection) -> None:
        """Add Phase 1.5 columns to existing SQLite databases."""
        migrations = {
            "event_verifications": [
                ("source_classification", "TEXT"),
                ("content_contains_official_claim", "INTEGER"),
            ],
            "predicted_assets": [
                ("asset_confidence", "REAL"),
                ("chain_confidence", "REAL"),
                ("anti_spurious_adjusted_confidence", "REAL"),
                ("final_confidence", "REAL"),
            ],
            "review_results": [
                ("predicted_direction", "TEXT"),
                ("is_directional_call", "INTEGER"),
                ("direction_evaluation_json", "TEXT"),
                ("asset_confidence", "REAL"),
                ("final_confidence", "REAL"),
            ],
            "rule_updates": [
                ("summary_id", "TEXT"),
            ],
        }
        for table, columns in migrations.items():
            existing = {
                row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            for column, definition in columns:
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
