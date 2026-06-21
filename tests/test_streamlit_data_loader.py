"""Tests for read-only Streamlit console data loading."""

from __future__ import annotations

import json
import sqlite3
from datetime import date

from eventalpha.news import EventLifecycleStore, TrackedEvent
from eventalpha.scheduler import SchedulerJobConfig, SchedulerRunRecord, SchedulerStateStore, TrackingPolicy
from eventalpha.schemas.base import utc_now
from eventalpha.ui import StreamlitDataLoader


def test_loader_handles_missing_files_without_creating_ledger(tmp_path) -> None:
    """Missing local files should become empty state, not writes."""
    missing_ledger = tmp_path / "missing.sqlite3"
    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=missing_ledger,
    ).load(briefing_date=date(2026, 6, 21))

    assert bundle["reports"] == []
    assert bundle["latest_report"] is None
    assert bundle["collected_data"].active_events == []
    assert not missing_ledger.exists()
    assert any("No local briefing reports" in note for note in bundle["notes"])


def test_loader_reads_briefing_report_files(tmp_path) -> None:
    """Markdown and JSON reports should be available to the console."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "daily_briefing_20260621.md").write_text("# Briefing", encoding="utf-8")
    (reports_dir / "daily_briefing_20260621.json").write_text(
        json.dumps({"title": "EventAlpha Daily Briefing - 2026-06-21"}),
        encoding="utf-8",
    )

    bundle = StreamlitDataLoader(
        reports_dir=reports_dir,
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
    ).load(briefing_date=date(2026, 6, 21))

    assert bundle["latest_report"].markdown == "# Briefing"
    assert bundle["latest_report"].json_payload["title"].endswith("2026-06-21")


def test_loader_reads_scheduler_lifecycle_and_tracking_state(tmp_path) -> None:
    """Scheduler runs, policies, and lifecycle events should load from local files."""
    now = utc_now()
    lifecycle_path = tmp_path / "lifecycle.json"
    lifecycle_store = EventLifecycleStore(lifecycle_path)
    lifecycle_store.upsert(
        TrackedEvent(
            canonical_title="AI export controls",
            lifecycle_stage="developing",
            first_seen_at=now,
            last_seen_at=now,
            sources=["Mock Wire"],
            source_count=1,
        )
    )
    lifecycle_store.save()

    scheduler_store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    scheduler_store.save_config([SchedulerJobConfig(job_id="status", job_type="scheduler_status")])
    scheduler_store.save_tracking_policies(
        [
            TrackingPolicy(
                tracked_event_id=lifecycle_store.list_events()[0].tracked_event_id,
                tracking_mode="normal",
                scan_interval_minutes=60,
                analyze=True,
                reason="test",
            )
        ]
    )
    scheduler_store.append_run(
        SchedulerRunRecord(job_id="status", job_type="scheduler_status").finish("success")
    )

    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=lifecycle_path,
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
    ).load(briefing_date=date(2026, 6, 21))

    data = bundle["collected_data"]
    assert data.active_events[0].canonical_title == "AI export controls"
    assert data.scheduler_jobs[0].job_id == "status"
    assert data.recent_runs[0].status == "success"
    assert data.tracking_policies[0].tracking_mode == "normal"


def test_loader_reads_ledger_rows_read_only(tmp_path) -> None:
    """Ledger-backed rows should be loaded via read-only collector queries."""
    ledger_path = tmp_path / "ledger.sqlite3"
    _create_ui_ledger_fixture(ledger_path)

    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=ledger_path,
    ).load(briefing_date=date(2026, 6, 21))

    data = bundle["collected_data"]
    assert data.event_cards[0]["event_title"] == "AI export event"
    assert data.review_results[0]["asset_name"] == "AI chips"
    assert data.rule_updates[0]["rule_id"] == "RULE_AI_EXPORT_001"


def _create_ui_ledger_fixture(path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                event_type TEXT
            );
            CREATE TABLE event_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT,
                event_id TEXT,
                event_title TEXT,
                event_level TEXT,
                credibility_score REAL,
                one_sentence TEXT,
                risk_factors_json TEXT,
                verification_indicators_json TEXT,
                risk_disclaimer TEXT,
                created_at TEXT
            );
            CREATE TABLE review_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id TEXT,
                prediction_id TEXT,
                event_id TEXT,
                horizon TEXT,
                asset_name TEXT,
                predicted_direction TEXT,
                actual_return REAL,
                benchmark_return REAL,
                excess_return REAL,
                direction_correct INTEGER,
                outperformed_benchmark INTEGER,
                causal_validity TEXT,
                review_conclusion TEXT,
                error_type TEXT,
                created_at TEXT
            );
            CREATE TABLE prediction_review_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_id TEXT,
                prediction_id TEXT,
                event_id TEXT,
                horizon TEXT,
                total_assets INTEGER,
                reviewed_assets INTEGER,
                direction_correct_count INTEGER,
                outperform_count INTEGER,
                average_excess_return REAL,
                conclusion_level TEXT,
                summary_text TEXT,
                error_types_json TEXT,
                rule_update_suggestions_json TEXT,
                created_at TEXT
            );
            CREATE TABLE rule_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                update_id TEXT,
                rule_id TEXT,
                prediction_id TEXT,
                review_id TEXT,
                summary_id TEXT,
                old_weight REAL,
                new_weight REAL,
                reason TEXT,
                update_action TEXT,
                created_at TEXT
            );
            INSERT INTO events (event_id, event_type) VALUES ('EVT_1', 'ai_export_control');
            INSERT INTO event_cards
            (card_id, event_id, event_title, event_level, credibility_score, one_sentence,
             risk_factors_json, verification_indicators_json, risk_disclaimer, created_at)
            VALUES ('CARD_1', 'EVT_1', 'AI export event', 'A', 0.8, 'summary',
                    '["risk"]', '["verify"]', 'risk disclaimer', '2026-06-21T00:00:00Z');
            INSERT INTO review_results
            (review_id, prediction_id, event_id, horizon, asset_name, predicted_direction,
             actual_return, benchmark_return, excess_return, direction_correct,
             outperformed_benchmark, causal_validity, review_conclusion, error_type, created_at)
            VALUES ('REV_1', 'PRED_1', 'EVT_1', 'T+1', 'AI chips', 'up',
                    0.03, 0.01, 0.02, 1, 1, 'valid', 'mock backed', 'none',
                    '2026-06-21T00:00:00Z');
            INSERT INTO prediction_review_summaries
            (summary_id, prediction_id, event_id, horizon, total_assets, reviewed_assets,
             direction_correct_count, outperform_count, average_excess_return,
             conclusion_level, summary_text, error_types_json, rule_update_suggestions_json, created_at)
            VALUES ('SUM_1', 'PRED_1', 'EVT_1', 'T+1', 1, 1, 1, 1, 0.02,
                    'valid', 'summary', '[]', '[]', '2026-06-21T00:00:00Z');
            INSERT INTO rule_updates
            (update_id, rule_id, prediction_id, review_id, summary_id, old_weight,
             new_weight, reason, update_action, created_at)
            VALUES ('UPD_1', 'RULE_AI_EXPORT_001', 'PRED_1', 'REV_1', 'SUM_1',
                    0.7, 0.75, 'worked', 'strengthen', '2026-06-21T00:00:00Z');
            """
        )
