"""Tests for daily briefing scheduler job integration."""

from __future__ import annotations

from datetime import date

from eventalpha.scheduler import JOB_RUNNERS, SchedulerJobConfig, SchedulerStateStore, run_daily_briefing_job


def test_daily_briefing_job_is_registered() -> None:
    """Scheduler registry should expose daily_briefing."""
    assert "daily_briefing" in JOB_RUNNERS


def test_daily_briefing_job_dry_run_does_not_write_reports(tmp_path) -> None:
    """Dry-run should append a run record but not write report files."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    record = run_daily_briefing_job(
        SchedulerJobConfig(job_id="daily_briefing", job_type="daily_briefing", dry_run=True),
        store,
        briefing_date=date(2026, 6, 21),
        reports_dir=tmp_path / "reports",
        ledger_path=tmp_path / "missing.sqlite3",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert record.status == "dry_run"
    assert not (tmp_path / "reports").exists()


def test_daily_briefing_job_execute_writes_reports(tmp_path) -> None:
    """Execute mode should write local report artifacts."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    record = run_daily_briefing_job(
        SchedulerJobConfig(job_id="daily_briefing", job_type="daily_briefing", dry_run=False),
        store,
        briefing_date=date(2026, 6, 21),
        reports_dir=tmp_path / "reports",
        ledger_path=tmp_path / "missing.sqlite3",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    assert record.status == "success"
    assert (tmp_path / "reports/daily_briefing_20260621.md").exists()
    assert (tmp_path / "reports/daily_briefing_20260621.json").exists()
