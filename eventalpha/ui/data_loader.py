"""Read-only data loading for the Streamlit event console."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import Field

from eventalpha.briefing import BriefingCollectedData, BriefingDataCollector
from eventalpha.schemas.base import EventAlphaModel


class BriefingReportFile(EventAlphaModel):
    """One local daily briefing report file pair."""

    briefing_date: date | None = None
    markdown_path: str
    json_path: str | None = None
    markdown: str = ""
    json_payload: dict[str, Any] = Field(default_factory=dict)


class StreamlitDataLoader:
    """Load local EventAlpha state without writes, fetches, LLM calls, or daemons."""

    def __init__(
        self,
        *,
        reports_dir: str | Path = "reports",
        lifecycle_store_path: str | Path = "data/event_lifecycle_store.json",
        state_path: str | Path = "data/scheduler_state.json",
        runs_path: str | Path = "data/scheduler_runs.jsonl",
        ledger_path: str | Path | None = None,
        max_items: int = 20,
    ) -> None:
        self.reports_dir = Path(reports_dir)
        self.lifecycle_store_path = Path(lifecycle_store_path)
        self.state_path = Path(state_path)
        self.runs_path = Path(runs_path)
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self.max_items = max(int(max_items), 1)

    def load(self, *, briefing_date: date | None = None) -> dict[str, Any]:
        """Return all console inputs as a read-only data bundle."""
        target_date = briefing_date or date.today()
        collector_kwargs: dict[str, Any] = {
            "lifecycle_store_path": self.lifecycle_store_path,
            "state_path": self.state_path,
            "runs_path": self.runs_path,
            "max_items": self.max_items,
        }
        if self.ledger_path is not None:
            collector_kwargs["ledger_path"] = self.ledger_path
        collected_data = BriefingDataCollector(**collector_kwargs).collect(target_date)
        reports = self.load_reports()
        latest_report = self.get_report_for_date(target_date, reports=reports) or (reports[0] if reports else None)
        notes = list(collected_data.notes)
        if not reports:
            notes.append(f"No local briefing reports found in {self.reports_dir}.")
        return {
            "briefing_date": target_date,
            "collected_data": collected_data,
            "reports": reports,
            "latest_report": latest_report,
            "notes": _dedupe(notes),
            "warnings": list(collected_data.warnings),
        }

    def load_reports(self) -> list[BriefingReportFile]:
        """Load local Markdown/JSON briefing files newest first."""
        if not self.reports_dir.exists():
            return []
        reports: list[BriefingReportFile] = []
        for markdown_path in sorted(self.reports_dir.glob("daily_briefing_*.md"), reverse=True):
            json_path = markdown_path.with_suffix(".json")
            payload: dict[str, Any] = {}
            if json_path.exists():
                try:
                    payload = json.loads(json_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    payload = {}
            reports.append(
                BriefingReportFile(
                    briefing_date=_date_from_report_name(markdown_path),
                    markdown_path=str(markdown_path),
                    json_path=str(json_path) if json_path.exists() else None,
                    markdown=markdown_path.read_text(encoding="utf-8"),
                    json_payload=payload,
                )
            )
        return reports

    def get_report_for_date(
        self,
        briefing_date: date,
        *,
        reports: list[BriefingReportFile] | None = None,
    ) -> BriefingReportFile | None:
        """Return the report for a specific date when present."""
        for report in reports if reports is not None else self.load_reports():
            if report.briefing_date == briefing_date:
                return report
        return None


def _date_from_report_name(path: Path) -> date | None:
    stem = path.stem.removeprefix("daily_briefing_")
    if len(stem) != 8 or not stem.isdigit():
        return None
    try:
        return date(int(stem[:4]), int(stem[4:6]), int(stem[6:8]))
    except ValueError:
        return None


def _dedupe(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results
