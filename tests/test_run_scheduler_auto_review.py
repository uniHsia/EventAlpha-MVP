"""Tests for run_scheduler review job helper."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.schemas.base import utc_now
from eventalpha.services import LedgerService
from scripts.run_scheduler import run_scheduler_once


def test_run_scheduler_review_due_scan_once(tmp_path) -> None:
    """CLI helper should run review_due_scan against a temp ledger."""
    ledger_path = _seed_due_ledger(tmp_path)

    result = run_scheduler_once(
        "review_due_scan",
        ledger_path=ledger_path,
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert result["record"].status == "dry_run"
    assert result["record"].candidate_items == 1


def test_run_scheduler_auto_review_dry_run_once(tmp_path) -> None:
    """CLI helper should preview auto_review_runner without writes."""
    ledger_path = _seed_due_ledger(tmp_path)

    result = run_scheduler_once(
        "auto_review_runner",
        ledger_path=ledger_path,
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert result["config"].dry_run is True
    assert result["record"].status == "dry_run"
    assert result["record"].candidate_items == 1


def test_run_scheduler_auto_review_execute_mock_once(tmp_path) -> None:
    """CLI helper should execute auto review with mock provider and temp ledger."""
    ledger_path = _seed_due_ledger(tmp_path)

    result = run_scheduler_once(
        "auto_review_runner",
        execute=True,
        market_provider="mock",
        ledger_path=ledger_path,
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert result["record"].status == "success"
    assert result["record"].candidate_items == 1
    assert result["record"].analyzed_events == 1
    assert result["record"].errors == []


def _seed_due_ledger(tmp_path) -> Path:
    ledger_path = tmp_path / "scheduler_cli_review.sqlite3"
    ledger = LedgerService(ledger_path)
    raw_news = RawNews(**json.loads((Path(__file__).parent / "fixtures/demo_events.json").read_text(encoding="utf-8"))[0])
    result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = result["prediction_ledger_entry"]
    task = ledger.get_review_tasks(prediction.prediction_id)[0]
    with ledger.repo.connect() as conn:
        conn.execute(
            "UPDATE review_tasks SET due_at = ? WHERE task_id = ?",
            ((utc_now() - timedelta(minutes=1)).isoformat(), task.task_id),
        )
        conn.commit()
    return ledger_path
