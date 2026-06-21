"""Tests for due review task asset counts."""

from __future__ import annotations

from eventalpha.scheduler import AutoReviewRunner

from utils_auto_review import seed_due_review_ledger


def test_due_task_view_counts_all_prediction_assets(tmp_path) -> None:
    """Due task views should count prediction assets, not horizon-filtered assets."""
    ledger = seed_due_review_ledger(tmp_path, horizon="T+1")

    views = AutoReviewRunner(ledger).scan_due_tasks()

    assert len(views) == 1
    assert views[0].horizon == "T+1"
    assert views[0].asset_count == 5
