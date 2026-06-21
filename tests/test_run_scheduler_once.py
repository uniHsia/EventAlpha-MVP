"""Tests for run_scheduler once helper."""

from __future__ import annotations

from scripts.run_scheduler import run_scheduler_once


def test_run_scheduler_once_news_lifecycle_default_dry_run(tmp_path) -> None:
    """Once-run scan should default to dry-run."""
    result = run_scheduler_once(
        "news_lifecycle_scan",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert result["config"].dry_run is True
    assert result["record"].status == "dry_run"
    assert result["record"].fetched_items > 0


def test_run_scheduler_once_scheduler_status(tmp_path) -> None:
    """Status once-run should complete and append a run record."""
    result = run_scheduler_once(
        "scheduler_status",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert result["record"].status == "success"
    assert (tmp_path / "runs.jsonl").exists()


def test_run_scheduler_once_execute_mock_scan(tmp_path) -> None:
    """Execute mock scan should succeed without real fetch."""
    result = run_scheduler_once(
        "news_lifecycle_scan",
        execute=True,
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert result["config"].dry_run is False
    assert result["config"].real_fetch is False
    assert result["record"].status == "success"
