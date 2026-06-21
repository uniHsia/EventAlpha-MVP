"""Tests for scheduler review job integration."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.schemas.base import utc_now
from eventalpha.scheduler import (
    JOB_RUNNERS,
    SchedulerJobConfig,
    SchedulerStateStore,
    run_auto_review_runner,
    run_review_due_scan,
)
from eventalpha.services import LedgerService


def test_review_jobs_are_registered() -> None:
    """Scheduler registry should expose review jobs."""
    assert "review_due_scan" in JOB_RUNNERS
    assert "auto_review_runner" in JOB_RUNNERS


def test_review_due_scan_run_record_counts_due_tasks(tmp_path) -> None:
    """Due scan job should map due tasks into scheduler counters."""
    ledger = _seed_due_tasks(tmp_path, due_count=1)
    record = run_review_due_scan(
        SchedulerJobConfig(job_id="review_due_scan", job_type="review_due_scan"),
        _store(tmp_path),
        ledger_service=ledger,
    )

    assert record.status == "dry_run"
    assert record.candidate_items == 1
    assert any("Due task:" in note for note in record.notes)


def test_auto_review_runner_job_preserves_summary_warnings(tmp_path) -> None:
    """Auto-review job should include summary warnings in run record."""
    ledger = _seed_due_tasks(tmp_path, due_count=1)

    def failing_pipeline(**kwargs):
        raise RuntimeError("market data missing")

    record = run_auto_review_runner(
        SchedulerJobConfig(
            job_id="auto_review_runner",
            job_type="auto_review_runner",
            dry_run=False,
            allow_partial_review=True,
        ),
        _store(tmp_path),
        ledger_service=ledger,
        review_pipeline_runner=failing_pipeline,
    )

    assert record.status == "success"
    assert record.candidate_items == 1
    assert record.analyzed_events == 0
    assert any("market data missing" in warning for warning in record.warnings)


def _seed_due_tasks(tmp_path, *, due_count: int) -> LedgerService:
    ledger = LedgerService(tmp_path / "scheduler_review.sqlite3")
    raw_news = RawNews(**json.loads((Path(__file__).parent / "fixtures/demo_events.json").read_text(encoding="utf-8"))[0])
    result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = result["prediction_ledger_entry"]
    tasks = ledger.get_review_tasks(prediction.prediction_id)
    now = utc_now()
    with ledger.repo.connect() as conn:
        for index, task in enumerate(tasks):
            due_at = now - timedelta(minutes=1) if index < due_count else now + timedelta(days=3)
            conn.execute("UPDATE review_tasks SET due_at = ? WHERE task_id = ?", (due_at.isoformat(), task.task_id))
        conn.commit()
    return ledger


def _store(tmp_path) -> SchedulerStateStore:
    return SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
