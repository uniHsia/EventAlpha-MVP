"""Read-only data loading for the Streamlit event console."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import Field

from eventalpha.briefing import BriefingCollectedData, BriefingDataCollector
from eventalpha.schemas.base import EventAlphaModel
from eventalpha.ui.components import (
    _build_recent_reviews,
    _build_recent_rule_updates,
    _build_top_events,
    build_dashboard_summary,
)
from eventalpha.ui.formatters import aggregate_warnings, format_warning_friendly


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
        historical_cases_path: str | Path = "data/historical_cases.json",
        max_items: int = 20,
        source_kind: str = "real",
        source_label: str | None = None,
    ) -> None:
        self.reports_dir = Path(reports_dir)
        self.lifecycle_store_path = Path(lifecycle_store_path)
        self.state_path = Path(state_path)
        self.runs_path = Path(runs_path)
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self.historical_cases_path = Path(historical_cases_path)
        self.max_items = max(int(max_items), 1)
        self.source_kind = source_kind if source_kind in {"real", "demo", "placeholder"} else "real"
        self.source_label = source_label or ("本地 Demo 数据" if self.source_kind == "demo" else "本地落盘数据")

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
        raw_warnings = aggregate_warnings(list(collected_data.warnings), limit=3)
        ui_ledger_rows = self._load_ui_ledger_rows(notes=notes)
        historical_cases = self.load_historical_cases(notes=notes)
        capability_reports = self.load_capability_reports(notes=notes)
        bundle: dict[str, Any] = {
            "briefing_date": target_date,
            "source_kind": self.source_kind,
            "source_label": self.source_label,
            "collected_data": collected_data,
            "reports": reports,
            "latest_report": latest_report,
            "notes": _dedupe(notes),
            "warnings": list(collected_data.warnings),
            "friendly_warnings": format_warning_friendly(raw_warnings),
            "top_events": _build_top_events(
                collected_data,
                source_kind=self.source_kind,
                source_label="Lifecycle Store" if self.source_kind == "real" else "Demo Lifecycle Store",
            ),
            "recent_reviews": _build_recent_reviews(
                collected_data,
                source_kind=self.source_kind,
                source_label="ReviewResult" if self.source_kind == "real" else "Demo ReviewResult",
            ),
            "recent_rule_updates": _build_recent_rule_updates(
                collected_data,
                source_kind=self.source_kind,
                source_label="RuleUpdate" if self.source_kind == "real" else "Demo RuleUpdate",
            ),
            "prediction_ledger_rows": ui_ledger_rows["prediction_ledger_rows"],
            "event_card_details": ui_ledger_rows["event_card_details"],
            "market_mappings": ui_ledger_rows["market_mappings"],
            "source_registry_rows": ui_ledger_rows["source_registry_rows"],
            "source_check_runs": ui_ledger_rows["source_check_runs"],
            "cluster_rows": ui_ledger_rows["cluster_rows"],
            "credibility_evidence_rows": ui_ledger_rows["credibility_evidence_rows"],
            "news_run_summary": ui_ledger_rows["news_run_summary"],
            "historical_cases": historical_cases,
            "capability_reports": capability_reports,
            "data_status": self._build_data_status(reports, latest_report),
        }
        bundle["dashboard_metrics"] = build_dashboard_summary(bundle).model_dump(mode="json")
        return {
            **bundle,
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

    def load_historical_cases(self, *, notes: list[str]) -> list[dict[str, Any]]:
        """Load local historical cases without seeding or writing the store."""
        if not self.historical_cases_path.exists():
            notes.append(f"No local historical case store found in {self.historical_cases_path}.")
            return []
        try:
            raw = json.loads(self.historical_cases_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            notes.append(f"Historical case store skipped: {exc}")
            return []
        cases = raw.get("cases", []) if isinstance(raw, dict) else []
        return [case for case in cases[: self.max_items] if isinstance(case, dict)]

    def load_capability_reports(self, *, notes: list[str]) -> dict[str, dict[str, Any]]:
        """Load latest local capability reports without generating them."""
        patterns = {
            "source_coverage": "source_coverage_*.json",
            "search_quality": "search_quality_*.json",
            "rule_feedback": "rule_feedback_signals_*.json",
            "push_outbox": "push_outbox_*.json",
        }
        reports: dict[str, dict[str, Any]] = {}
        for key, pattern in patterns.items():
            path = _latest_json_report(self.reports_dir, pattern)
            if path is None:
                notes.append(f"No local {key} report found in {self.reports_dir}.")
                reports[key] = {}
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                notes.append(f"{key} report skipped: {exc}")
                reports[key] = {}
                continue
            payload["_path"] = str(path)
            reports[key] = payload if isinstance(payload, dict) else {}
        return reports

    def _load_ui_ledger_rows(self, *, notes: list[str]) -> dict[str, Any]:
        """Load homepage-only SQLite rows without touching backend services."""
        empty = {
            "prediction_ledger_rows": [],
            "event_card_details": [],
            "market_mappings": [],
            "source_registry_rows": [],
            "source_check_runs": [],
            "cluster_rows": [],
            "credibility_evidence_rows": [],
            "news_run_summary": {},
        }
        ledger_path = self._resolved_ledger_path()
        if ledger_path is None or not Path(ledger_path).exists():
            return empty

        uri = Path(ledger_path).resolve().as_uri() + "?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                return {
                    "prediction_ledger_rows": self._query_prediction_ledger_rows(conn),
                    "event_card_details": self._query_event_card_details(conn),
                    "market_mappings": self._query_market_mappings(conn),
                    "source_registry_rows": self._query_source_registry_rows(conn),
                    "source_check_runs": self._query_source_check_runs(conn),
                    "cluster_rows": self._query_cluster_rows(conn),
                    "credibility_evidence_rows": self._query_credibility_evidence_rows(conn),
                    "news_run_summary": self._query_news_run_summary(conn),
                }
        except sqlite3.Error as exc:
            notes.append(f"Homepage read-only ledger query skipped: {exc}")
            return empty

    def _query_prediction_ledger_rows(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT p.id AS ledger_row_id,
                       p.prediction_id,
                       p.event_id,
                       p.event_title,
                       p.event_type,
                       p.publish_time,
                       p.event_level,
                       p.credibility_score,
                       p.impact_score,
                       p.status,
                       p.created_at AS prediction_created_at,
                       a.asset_name,
                       a.asset_type,
                       a.direction,
                       a.time_window,
                       a.asset_confidence,
                       a.chain_confidence,
                       a.anti_spurious_adjusted_confidence,
                       a.final_confidence,
                       a.confidence,
                       a.benchmark,
                       a.created_at AS asset_created_at
                FROM prediction_ledger p
                LEFT JOIN predicted_assets a ON a.prediction_id = p.prediction_id
                ORDER BY p.id DESC, a.id ASC
                LIMIT ?
                """,
                (self.max_items,),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []

    def _query_event_card_details(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT card_id,
                       event_id,
                       event_title,
                       what_happened,
                       sources_json,
                       causal_chain_summary_json,
                       possible_impacts_json,
                       risk_factors_json,
                       verification_indicators_json,
                       history_validation_summary_json,
                       source_evidence_json,
                       verification_status,
                       official_confirmation,
                       staleness_flag,
                       prediction_gate_status,
                       prediction_gate_reason,
                       created_at
                FROM event_cards
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.max_items,),
            ).fetchall()
            return [_decode_json_fields(dict(row)) for row in rows]
        except sqlite3.Error:
            return []

    def _query_market_mappings(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT mapping_id,
                       event_id,
                       mapped_assets_json,
                       watch_indicators_json,
                       mapping_notes,
                       created_at
                FROM market_mappings
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.max_items,),
            ).fetchall()
            return [_decode_json_fields(dict(row)) for row in rows]
        except sqlite3.Error:
            return []

    def _query_source_registry_rows(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT source_name, source_type, enabled, region, language,
                       credibility_base, fetch_mode, notes, updated_at
                FROM news_sources
                ORDER BY source_type ASC, source_name ASC
                LIMIT ?
                """,
                (self.max_items * 3,),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []

    def _query_source_check_runs(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT check_run_id, source_run_id, source_name, query, status,
                       fetched_at, item_count, error_text, raw_result_notes, created_at
                FROM source_check_runs
                ORDER BY fetched_at DESC, id DESC
                LIMIT ?
                """,
                (self.max_items * 3,),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []

    def _query_cluster_rows(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT cluster_record_id, source_run_id, cluster_id, canonical_title,
                       canonical_summary, source_count, item_count, unique_source_count,
                       mainstream_source_count, cluster_type, independent_confirmation,
                       first_seen_at, last_seen_at, dominant_keywords_json,
                       candidate_event_type, verification_status, confidence,
                       debug_reasons_json, created_at
                FROM event_clusters
                ORDER BY last_seen_at DESC, id DESC
                LIMIT ?
                """,
                (self.max_items * 3,),
            ).fetchall()
            return [_decode_json_fields(dict(row)) for row in rows]
        except sqlite3.Error:
            return []

    def _query_credibility_evidence_rows(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT evidence_record_id, source_run_id, cluster_id, event_id, evidence_key,
                       source_name, evidence_type, claim_text, supporting_item_ids_json,
                       supporting_sources_json, consistency_status, official_evidence_status,
                       risk_flags_json, note_text, created_at
                FROM credibility_evidence
                ORDER BY id DESC
                LIMIT ?
                """,
                (self.max_items * 6,),
            ).fetchall()
            return [_decode_json_fields(dict(row)) for row in rows]
        except sqlite3.Error:
            return []

    def _query_news_run_summary(self, conn: sqlite3.Connection) -> dict[str, Any]:
        try:
            latest = conn.execute(
                """
                SELECT source_run_id, MAX(fetched_at) AS fetched_at
                FROM source_check_runs
                WHERE source_run_id IS NOT NULL
                GROUP BY source_run_id
                ORDER BY fetched_at DESC, source_run_id DESC
                LIMIT 1
                """
            ).fetchone()
        except sqlite3.Error:
            return {}
        if latest is None or not latest["source_run_id"]:
            return {}
        source_run_id = latest["source_run_id"]

        def _count(query: str) -> int:
            try:
                row = conn.execute(query, (source_run_id,)).fetchone()
            except sqlite3.Error:
                return 0
            return int(row[0] or 0) if row is not None else 0

        summary: dict[str, Any] = {
            "latest_source_run_id": source_run_id,
            "latest_checked_at": latest["fetched_at"],
            "source_check_runs_count": _count("SELECT COUNT(*) FROM source_check_runs WHERE source_run_id = ?"),
            "raw_news_items_count": _count("SELECT COUNT(*) FROM raw_news_items WHERE source_run_id = ?"),
            "dedup_news_count": _count("SELECT COUNT(*) FROM raw_news_items WHERE source_run_id = ? AND IFNULL(is_duplicate, 0) = 0"),
            "event_clusters_count": _count("SELECT COUNT(*) FROM event_clusters WHERE source_run_id = ?"),
            "cluster_news_links_count": _count("SELECT COUNT(*) FROM cluster_news_links WHERE source_run_id = ?"),
            "credibility_evidence_count": _count("SELECT COUNT(*) FROM credibility_evidence WHERE source_run_id = ?"),
        }

        try:
            source_rows = conn.execute(
                """
                SELECT source_name, status, item_count, error_text, fetched_at
                FROM source_check_runs
                WHERE source_run_id = ?
                ORDER BY fetched_at DESC, id DESC
                """,
                (source_run_id,),
            ).fetchall()
        except sqlite3.Error:
            source_rows = []
        summary["source_status_rows"] = [dict(row) for row in source_rows]

        try:
            cluster_rows = conn.execute(
                """
                SELECT cluster_type, item_count, unique_source_count, independent_confirmation,
                       verification_status, confidence
                FROM event_clusters
                WHERE source_run_id = ?
                ORDER BY id DESC
                """,
                (source_run_id,),
            ).fetchall()
        except sqlite3.Error:
            cluster_rows = []
        summary["cluster_rows"] = [dict(row) for row in cluster_rows]

        try:
            event_cards_row = conn.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN source_evidence_json IS NOT NULL AND source_evidence_json != '[]' THEN 1 ELSE 0 END) AS with_source_evidence,
                       SUM(CASE WHEN prediction_gate_status = 'written' THEN 1 ELSE 0 END) AS written_count,
                       SUM(CASE WHEN prediction_gate_status IS NOT NULL AND prediction_gate_status != 'written' THEN 1 ELSE 0 END) AS skipped_count
                FROM event_cards
                WHERE event_id IN (
                    SELECT e.event_id
                    FROM events e
                    JOIN raw_news r ON r.raw_id = e.raw_id
                    WHERE r.source_run_id = ?
                )
                """,
                (source_run_id,),
            ).fetchone()
        except sqlite3.Error:
            event_cards_row = None
        if event_cards_row is not None:
            summary["event_cards_count"] = int(event_cards_row["total"] or 0)
            summary["event_cards_with_source_evidence_count"] = int(event_cards_row["with_source_evidence"] or 0)
            summary["written_event_cards_count"] = int(event_cards_row["written_count"] or 0)
            summary["skipped_event_cards_count"] = int(event_cards_row["skipped_count"] or 0)

        try:
            gate_rows = conn.execute(
                """
                SELECT prediction_gate_status, COUNT(*) AS count
                FROM event_cards
                WHERE event_id IN (
                    SELECT e.event_id
                    FROM events e
                    JOIN raw_news r ON r.raw_id = e.raw_id
                    WHERE r.source_run_id = ?
                )
                GROUP BY prediction_gate_status
                """,
                (source_run_id,),
            ).fetchall()
        except sqlite3.Error:
            gate_rows = []
        summary["prediction_gate_breakdown"] = [
            {"status": row["prediction_gate_status"], "count": int(row["count"] or 0)}
            for row in gate_rows
        ]

        try:
            ledger_row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM prediction_ledger
                WHERE event_id IN (
                    SELECT e.event_id
                    FROM events e
                    JOIN raw_news r ON r.raw_id = e.raw_id
                    WHERE r.source_run_id = ?
                )
                """,
                (source_run_id,),
            ).fetchone()
        except sqlite3.Error:
            ledger_row = None
        summary["ledger_prediction_count"] = int(ledger_row["total"] or 0) if ledger_row else 0
        return summary

    def _build_data_status(self, reports: list[BriefingReportFile], latest_report: BriefingReportFile | None) -> dict[str, Any]:
        ledger_path = self._resolved_ledger_path()
        return {
            "reports_count": len(reports),
            "latest_report_path": latest_report.markdown_path if latest_report else None,
            "reports_dir_exists": self.reports_dir.exists(),
            "lifecycle_store_exists": self.lifecycle_store_path.exists(),
            "scheduler_state_exists": self.state_path.exists(),
            "scheduler_runs_exists": self.runs_path.exists(),
            "ledger_exists": bool(ledger_path and Path(ledger_path).exists()),
            "historical_cases_exists": self.historical_cases_path.exists(),
            "historical_cases_path": str(self.historical_cases_path),
        }

    def _resolved_ledger_path(self) -> Path | None:
        if self.ledger_path is not None:
            return self.ledger_path
        try:
            from eventalpha.config import get_db_path

            return Path(get_db_path())
        except Exception:
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


def _decode_json_fields(row: dict[str, Any]) -> dict[str, Any]:
    for key, value in list(row.items()):
        if key.endswith("_json"):
            target_key = key.removesuffix("_json")
            try:
                row[target_key] = json.loads(value) if value else []
            except json.JSONDecodeError:
                row[target_key] = []
    return row


def _latest_json_report(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    matches = sorted(directory.glob(pattern), reverse=True)
    return matches[0] if matches else None
