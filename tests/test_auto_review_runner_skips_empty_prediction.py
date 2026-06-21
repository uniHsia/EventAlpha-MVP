"""Tests for empty-prediction auto-review behavior."""

from __future__ import annotations

from eventalpha.scheduler import AutoReviewRunner

from utils_auto_review import seed_empty_prediction_due_task


def test_auto_review_runner_skips_prediction_without_assets(tmp_path) -> None:
    """Predictions with no assets should not be marked completed or produce rules."""
    ledger = seed_empty_prediction_due_task(tmp_path)
    prediction = ledger.get_latest_prediction()
    assert prediction is not None

    summary = AutoReviewRunner(ledger).run(dry_run=False, market_provider="mock")
    task = ledger.get_review_tasks(prediction.prediction_id)[0]

    assert summary.reviewed_task_count == 0
    assert summary.skipped_task_count == 1
    assert summary.review_result_count == 0
    assert summary.rule_update_count == 0
    assert task.status == "pending"
    assert ledger.get_review_results(prediction.prediction_id) == []
    assert ledger.get_rule_updates(prediction.prediction_id) == []
    assert any("no_predicted_assets" in warning for warning in summary.warnings)
