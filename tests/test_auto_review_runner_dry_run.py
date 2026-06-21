"""Dry-run safety tests for AutoReviewRunner."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.schemas.base import utc_now
from eventalpha.scheduler import AutoReviewRunner
from eventalpha.services import LedgerService


def test_auto_review_runner_dry_run_returns_views_without_pipeline_or_writes(tmp_path) -> None:
    """Dry-run should show due task views and avoid review side effects."""
    ledger = _seed_one_due_task(tmp_path)
    prediction = ledger.get_latest_prediction()
    assert prediction is not None

    def fail_pipeline(**kwargs):
        raise AssertionError("review pipeline should not be called during dry-run")

    summary = AutoReviewRunner(ledger, review_pipeline_runner=fail_pipeline).run(
        dry_run=True,
        market_provider="akshare",
    )

    assert summary.due_task_count == 1
    assert summary.skipped_task_count == 1
    assert summary.due_tasks[0].event_title == prediction.event_title
    assert summary.due_tasks[0].prediction_id == prediction.prediction_id
    assert ledger.get_review_results(prediction.prediction_id) == []
    assert ledger.list_due_review_tasks(limit=5)
    assert any("market provider were not called" in note for note in summary.notes)


def _seed_one_due_task(tmp_path) -> LedgerService:
    ledger = LedgerService(tmp_path / "dry_run.sqlite3")
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
    return ledger
