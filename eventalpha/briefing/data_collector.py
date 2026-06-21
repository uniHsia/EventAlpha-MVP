"""Read-only local data collection for daily briefings."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from eventalpha.config import get_db_path
from eventalpha.news import DEFAULT_LIFECYCLE_STORE_PATH, EventLifecycleStore
from eventalpha.scheduler.priority_ranker import EventPriorityRanker
from eventalpha.scheduler.state_store import (
    DEFAULT_SCHEDULER_RUNS_PATH,
    DEFAULT_SCHEDULER_STATE_PATH,
    SchedulerStateStore,
)

from .schemas import BriefingCollectedData


class BriefingDataCollector:
    """Collect briefing inputs without fetching, running providers, or writing ledger."""

    def __init__(
        self,
        *,
        lifecycle_store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
        state_path: str | Path = DEFAULT_SCHEDULER_STATE_PATH,
        runs_path: str | Path = DEFAULT_SCHEDULER_RUNS_PATH,
        ledger_path: str | Path | None = None,
        max_items: int = 10,
    ) -> None:
        self.lifecycle_store_path = Path(lifecycle_store_path)
        self.scheduler_store = SchedulerStateStore(state_path=state_path, runs_path=runs_path)
        self.ledger_path = Path(ledger_path) if ledger_path else get_db_path()
        self.max_items = max(max_items, 1)
        self.query_limit = max(self.max_items * 5, 50)

    def collect(self, briefing_date: date) -> BriefingCollectedData:
        """Collect local state for one briefing date."""
        warnings: list[str] = []
        notes: list[str] = []

        try:
            active_events = EventLifecycleStore(self.lifecycle_store_path).load().list_active_events()
        except Exception as exc:  # pragma: no cover - defensive read boundary
            active_events = []
            warnings.append(f"Lifecycle store read failed: {exc}")

        urgency_scores = EventPriorityRanker().rank(active_events) if active_events else []
        scheduler_jobs = self.scheduler_store.load_config()
        recent_runs = self.scheduler_store.list_recent_runs(limit=max(self.max_items, 20))
        tracking_policies = self.scheduler_store.load_tracking_policies()

        for run in recent_runs:
            if run.job_type != "daily_briefing":
                warnings.extend(run.warnings)
            warnings.extend(run.errors)

        ledger_rows = self._read_ledger_rows(notes=notes, warnings=warnings)
        if not active_events:
            notes.append("No active lifecycle events found in local store.")
        if not recent_runs:
            notes.append("No scheduler run records found.")

        return BriefingCollectedData(
            briefing_date=briefing_date,
            active_events=active_events,
            urgency_scores=urgency_scores,
            scheduler_jobs=scheduler_jobs,
            recent_runs=recent_runs,
            tracking_policies=tracking_policies,
            event_cards=ledger_rows["event_cards"],
            review_results=ledger_rows["review_results"],
            review_summaries=ledger_rows["review_summaries"],
            rule_updates=ledger_rows["rule_updates"],
            warnings=list(warnings),
            notes=_dedupe(notes),
        )

    def _read_ledger_rows(self, *, notes: list[str], warnings: list[str]) -> dict[str, list[dict[str, Any]]]:
        empty = {
            "event_cards": [],
            "review_results": [],
            "review_summaries": [],
            "rule_updates": [],
        }
        if not self.ledger_path.exists():
            notes.append(f"Ledger file not found; skipped ledger-backed briefing data: {self.ledger_path}")
            return empty

        uri = self.ledger_path.resolve().as_uri() + "?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                return {
                    "event_cards": self._query_event_cards(conn),
                    "review_results": self._query_rows(
                        conn,
                        """
                        SELECT id, review_id, prediction_id, event_id, horizon, asset_name,
                               predicted_direction, actual_return, benchmark_return,
                               excess_return, direction_correct, outperformed_benchmark,
                               causal_validity, review_conclusion, error_type, created_at
                        FROM review_results
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                    ),
                    "review_summaries": self._query_rows(
                        conn,
                        """
                        SELECT id, summary_id, prediction_id, event_id, horizon, total_assets,
                               reviewed_assets, direction_correct_count, outperform_count,
                               average_excess_return, conclusion_level, summary_text,
                               error_types_json, rule_update_suggestions_json, created_at
                        FROM prediction_review_summaries
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                    ),
                    "rule_updates": self._query_rows(
                        conn,
                        """
                        SELECT id, update_id, rule_id, prediction_id, review_id, summary_id,
                               old_weight, new_weight, reason, update_action, created_at
                        FROM rule_updates
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                    ),
                }
        except sqlite3.Error as exc:
            warnings.append(f"Read-only ledger query failed: {exc}")
            return empty

    def _query_event_cards(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            return self._query_rows(
                conn,
                """
                SELECT c.id, c.card_id, c.event_id, c.event_title,
                       e.event_type, c.event_level, c.credibility_score,
                       c.one_sentence, c.risk_factors_json,
                       c.verification_indicators_json, c.risk_disclaimer,
                       c.created_at
                FROM event_cards c
                LEFT JOIN events e ON e.event_id = c.event_id
                ORDER BY c.id DESC
                LIMIT ?
                """,
            )
        except sqlite3.Error:
            return self._query_rows(
                conn,
                """
                SELECT id, card_id, event_id, event_title, NULL AS event_type,
                       event_level, credibility_score, one_sentence,
                       risk_factors_json, verification_indicators_json,
                       risk_disclaimer, created_at
                FROM event_cards
                ORDER BY id DESC
                LIMIT ?
                """,
            )

    def _query_rows(self, conn: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
        rows = conn.execute(sql, (self.query_limit,)).fetchall()
        return [_decode_json_fields(dict(row)) for row in rows]


def _decode_json_fields(row: dict[str, Any]) -> dict[str, Any]:
    for key, value in list(row.items()):
        if key.endswith("_json"):
            target_key = key.removesuffix("_json")
            try:
                row[target_key] = json.loads(value) if value else []
            except json.JSONDecodeError:
                row[target_key] = []
    return row


def _dedupe(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results
