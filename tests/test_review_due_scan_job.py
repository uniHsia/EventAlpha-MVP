"""Tests for the review_due_scan scheduler job."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.schemas.base import utc_now
from eventalpha.scheduler import SchedulerJobConfig, SchedulerStateStore, run_review_due_scan
from eventalpha.services import LedgerService


def test_review_due_scan_finds_due_pending_tasks_only(tmp_path) -> None:
    """Due scan should include pending due tasks and exclude future/completed tasks."""
    ledger = _seed_ledger_with_due_tasks(tmp_path)
    store = _store(tmp_path)

    record = run_review_due_scan(
        SchedulerJobConfig(job_id="review_due_scan", job_type="review_due_scan", dry_run=True),
        store,
        ledger_service=ledger,
    )

    assert record.status == "dry_run"
    assert record.candidate_items == 1
    assert any("Due task:" in note and "T+1" in note for note in record.notes)
    prediction = ledger.get_latest_prediction()
    assert prediction is not None
    assert ledger.get_review_results(prediction.prediction_id) == []


def test_review_due_scan_horizon_filter(tmp_path) -> None:
    """Horizon filters should limit the due scan."""
    ledger = _seed_ledger_with_due_tasks(tmp_path)
    store = _store(tmp_path)

    record = run_review_due_scan(
        SchedulerJobConfig(
            job_id="review_due_scan",
            job_type="review_due_scan",
            dry_run=True,
            review_horizons=["T+3"],
        ),
        store,
        ledger_service=ledger,
    )

    assert record.candidate_items == 0


def _seed_ledger_with_due_tasks(tmp_path) -> LedgerService:
    ledger = LedgerService(tmp_path / "review_due.sqlite3")
    raw_news = RawNews(**json.loads((Path(__file__).parent / "fixtures/demo_events.json").read_text(encoding="utf-8"))[0])
    result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = result["prediction_ledger_entry"]
    tasks = ledger.get_review_tasks(prediction.prediction_id)
    now = utc_now()
    with ledger.repo.connect() as conn:
        conn.execute(
            "UPDATE review_tasks SET due_at = ? WHERE task_id = ?",
            ((now - timedelta(minutes=1)).isoformat(), tasks[0].task_id),
        )
        conn.execute(
            "UPDATE review_tasks SET due_at = ? WHERE task_id = ?",
            ((now + timedelta(days=5)).isoformat(), tasks[1].task_id),
        )
        conn.execute(
            "UPDATE review_tasks SET due_at = ?, status = 'completed' WHERE task_id = ?",
            ((now - timedelta(days=1)).isoformat(), tasks[2].task_id),
        )
        conn.commit()
    return ledger


def _store(tmp_path) -> SchedulerStateStore:
    return SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
