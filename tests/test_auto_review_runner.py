"""Tests for AutoReviewRunner execute behavior."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.schemas.base import utc_now
from eventalpha.scheduler import AutoReviewRunner
from eventalpha.services import LedgerService


def test_auto_review_runner_execute_reviews_due_task_and_marks_completed(tmp_path) -> None:
    """Execute mode should run the review pipeline and complete successful tasks."""
    ledger = _seed_due_tasks(tmp_path, due_count=1)
    calls = []

    def fake_pipeline(**kwargs):
        calls.append(kwargs)
        return {"review_results": [object(), object()], "rule_update": object()}

    summary = AutoReviewRunner(ledger, review_pipeline_runner=fake_pipeline).run(
        dry_run=False,
        market_provider="mock",
    )

    task = ledger.list_due_review_tasks(limit=5)
    assert summary.due_task_count == 1
    assert summary.reviewed_task_count == 1
    assert summary.review_result_count == 2
    assert summary.rule_update_count == 1
    assert calls
    assert task == []
    prediction = ledger.get_latest_prediction()
    assert prediction is not None
    assert all(review_task.status == "completed" for review_task in ledger.get_review_tasks(prediction.prediction_id)[:1])


def test_auto_review_runner_partial_failure_continues_other_tasks(tmp_path) -> None:
    """Partial failure should not abort later due tasks."""
    ledger = _seed_due_tasks(tmp_path, due_count=2)
    calls = []

    def flaky_pipeline(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("provider unavailable")
        return {"review_results": [object()], "rule_update": object()}

    summary = AutoReviewRunner(ledger, review_pipeline_runner=flaky_pipeline).run(
        dry_run=False,
        market_provider="mock",
        allow_partial_review=True,
    )

    assert summary.due_task_count == 2
    assert summary.reviewed_task_count == 1
    assert summary.skipped_task_count == 1
    assert summary.failed_task_count == 0
    assert summary.review_result_count == 1
    assert any("provider unavailable" in warning for warning in summary.warnings)
    assert len(calls) == 2


def test_auto_review_runner_strict_failure_records_error(tmp_path) -> None:
    """Strict mode should record task failures as errors."""
    ledger = _seed_due_tasks(tmp_path, due_count=1)

    def failing_pipeline(**kwargs):
        raise RuntimeError("hard failure")

    summary = AutoReviewRunner(ledger, review_pipeline_runner=failing_pipeline).run(
        dry_run=False,
        market_provider="mock",
        allow_partial_review=False,
    )

    assert summary.failed_task_count == 1
    assert summary.errors


def _seed_due_tasks(tmp_path, *, due_count: int) -> LedgerService:
    ledger = LedgerService(tmp_path / "auto_review.sqlite3")
    raw_news = RawNews(**json.loads((Path(__file__).parent / "fixtures/demo_events.json").read_text(encoding="utf-8"))[0])
    result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = result["prediction_ledger_entry"]
    tasks = ledger.get_review_tasks(prediction.prediction_id)
    now = utc_now()
    with ledger.repo.connect() as conn:
        for index, task in enumerate(tasks):
            due_at = now - timedelta(minutes=1) if index < due_count else now + timedelta(days=3)
            conn.execute(
                "UPDATE review_tasks SET due_at = ? WHERE task_id = ?",
                (due_at.isoformat(), task.task_id),
            )
        conn.commit()
    return ledger
