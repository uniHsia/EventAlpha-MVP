"""Tests that zero-result reviews are not counted as successful."""

from __future__ import annotations

from eventalpha.scheduler import AutoReviewRunner

from utils_auto_review import seed_due_review_ledger


def test_zero_review_results_do_not_complete_task(tmp_path) -> None:
    """A pipeline returning zero results should skip the task, not complete it."""
    ledger = seed_due_review_ledger(tmp_path, horizon="T+1")
    prediction = ledger.get_latest_prediction()
    assert prediction is not None

    def empty_pipeline(**kwargs):
        return {"review_results": [], "rule_update": object()}

    summary = AutoReviewRunner(ledger, review_pipeline_runner=empty_pipeline).run(
        dry_run=False,
        market_provider="mock",
    )
    task = ledger.get_review_tasks(prediction.prediction_id)[0]

    assert summary.reviewed_task_count == 0
    assert summary.skipped_task_count == 1
    assert summary.review_result_count == 0
    assert summary.rule_update_count == 0
    assert task.status == "pending"
    assert any("no_review_results" in warning for warning in summary.warnings)
