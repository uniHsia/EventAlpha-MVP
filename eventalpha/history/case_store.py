"""JSON-backed historical case store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eventalpha.schemas.base import utc_now

from .schemas import HistoricalCase


DEFAULT_HISTORICAL_CASE_STORE_PATH = Path("data/historical_cases.json")


class HistoricalCaseStore:
    """Persist historical cases in a small readable JSON file."""

    def __init__(self, path: str | Path = DEFAULT_HISTORICAL_CASE_STORE_PATH) -> None:
        self.path = Path(path)
        self.cases: dict[str, HistoricalCase] = {}

    def load(self) -> "HistoricalCaseStore":
        """Load cases from JSON if the file exists."""
        if not self.path.exists():
            self.cases = {}
            return self
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        cases = raw.get("cases", []) if isinstance(raw, dict) else []
        self.cases = {
            case.case_id: case
            for case in (HistoricalCase.model_validate(item) for item in cases)
        }
        return self

    def save(self) -> None:
        """Save cases to JSON."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "updated_at": utc_now().isoformat(),
            "cases": [case.model_dump(mode="json") for case in self.list_cases()],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, historical_case: HistoricalCase) -> None:
        """Insert or replace a historical case."""
        self.cases[historical_case.case_id] = historical_case

    def get(self, case_id: str) -> HistoricalCase | None:
        """Return one case by ID."""
        return self.cases.get(case_id)

    def list_cases(self) -> list[HistoricalCase]:
        """Return cases sorted by date and title."""
        return sorted(
            self.cases.values(),
            key=lambda case: (case.event_date is not None, case.event_date or "", case.title),
            reverse=True,
        )

    def reset(self) -> None:
        """Clear in-memory and persisted cases."""
        self.cases = {}
        if self.path.exists():
            self.path.unlink()
