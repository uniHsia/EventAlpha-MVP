"""Tests that auto review generates asset-level results."""

from __future__ import annotations

from eventalpha.scheduler import AutoReviewRunner

from utils_auto_review import seed_due_review_ledger


def test_auto_review_runner_execute_generates_review_results(tmp_path) -> None:
    """Execute + mock provider should create one ReviewResult per predicted asset."""
    ledger = seed_due_review_ledger(tmp_path, horizon="T+1")
    prediction = ledger.get_latest_prediction()
    assert prediction is not None

    summary = AutoReviewRunner(ledger).run(dry_run=False, market_provider="mock")

    review_rows = ledger.get_review_results(prediction.prediction_id)
    task = ledger.get_review_tasks(prediction.prediction_id)[0]
    assert summary.reviewed_task_count == 1
    assert summary.review_result_count == len(prediction.predicted_assets) == 5
    assert summary.rule_update_count == 1
    assert len(review_rows) == 5
    assert task.status == "completed"
    assert any("assets=5 results=5 rule_updates=1" in note for note in summary.notes)
