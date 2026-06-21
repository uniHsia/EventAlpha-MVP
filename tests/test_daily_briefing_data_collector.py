"""Tests for daily briefing data collection."""

from __future__ import annotations

import sqlite3
from datetime import date

from eventalpha.briefing import BriefingDataCollector
from eventalpha.scheduler import SchedulerJobConfig, SchedulerRunRecord, SchedulerStateStore


def test_collector_handles_empty_state_without_creating_ledger(tmp_path) -> None:
    """Missing local data should produce notes, not writes or crashes."""
    missing_ledger = tmp_path / "missing.sqlite3"
    data = BriefingDataCollector(
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=missing_ledger,
    ).collect(date(2026, 6, 21))

    assert data.active_events == []
    assert data.event_cards == []
    assert any("Ledger file not found" in note for note in data.notes)
    assert not missing_ledger.exists()


def test_collector_reads_scheduler_runs_and_dedupes_warnings(tmp_path) -> None:
    """Scheduler warnings should be collected once."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    store.save_config([SchedulerJobConfig(job_id="scheduler_status", job_type="scheduler_status")])
    store.append_run(
        SchedulerRunRecord(
            job_id="news_lifecycle_scan",
            job_type="news_lifecycle_scan",
            status="success",
            warnings=["RSS query matched no items.", "RSS query matched no items."],
        ).finish("success")
    )

    data = BriefingDataCollector(
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
    ).collect(date(2026, 6, 21))

    assert len(data.scheduler_jobs) == 1
    assert len(data.recent_runs) == 1
    assert data.warnings.count("RSS query matched no items.") == 1


def test_collector_reads_ledger_rows_read_only(tmp_path) -> None:
    """Existing ledger rows should be available without LedgerService initialization."""
    ledger_path = tmp_path / "briefing.sqlite3"
    with sqlite3.connect(ledger_path) as conn:
        conn.execute(
            """
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
            )
            """
        )
        conn.execute(
            """
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
            )
            """
        )
        conn.execute(
            """
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
            )
            """
        )
        conn.execute(
            """
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
            )
            """
        )
        conn.execute(
            """
            INSERT INTO event_cards
            (card_id, event_id, event_title, event_level, credibility_score, one_sentence,
             risk_factors_json, verification_indicators_json, risk_disclaimer, created_at)
            VALUES ('CARD_1', 'EVT_1', 'AI export event', 'A', 0.9, 'summary',
                    '["demo history signal"]', '["verify official source"]', 'risk', '2026-06-21')
            """
        )
        conn.commit()

    data = BriefingDataCollector(
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=ledger_path,
    ).collect(date(2026, 6, 21))

    assert data.event_cards[0]["event_title"] == "AI export event"
    assert data.event_cards[0]["risk_factors"] == ["demo history signal"]
