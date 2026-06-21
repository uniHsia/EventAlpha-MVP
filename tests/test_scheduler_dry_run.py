"""Tests for scheduler dry-run safety boundaries."""

from __future__ import annotations

from pathlib import Path

from eventalpha.scheduler import SchedulerJobConfig, SchedulerStateStore, run_candidate_analysis, run_news_lifecycle_scan


def test_news_lifecycle_dry_run_does_not_write_lifecycle_store(tmp_path) -> None:
    """Dry-run scan should not create the lifecycle store."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    lifecycle_path = tmp_path / "lifecycle.json"

    run_news_lifecycle_scan(
        SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", dry_run=True),
        store,
        lifecycle_store_path=lifecycle_path,
    )

    assert not lifecycle_path.exists()


def test_candidate_analysis_dry_run_does_not_call_pipeline_or_write_ledger(tmp_path) -> None:
    """Candidate dry-run should not call pipeline or touch default SQLite."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    lifecycle_path = tmp_path / "lifecycle.json"
    run_news_lifecycle_scan(
        SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", dry_run=False),
        store,
        lifecycle_store_path=lifecycle_path,
    )
    ledger_path = Path("eventalpha_mvp.sqlite3")
    before_mtime = ledger_path.stat().st_mtime_ns if ledger_path.exists() else None

    def fail_pipeline(*args, **kwargs):
        raise AssertionError("pipeline should not be called")

    record = run_candidate_analysis(
        SchedulerJobConfig(job_id="candidate", job_type="candidate_analysis", dry_run=True),
        store,
        lifecycle_store_path=lifecycle_path,
        pipeline_runner=fail_pipeline,
    )

    after_mtime = ledger_path.stat().st_mtime_ns if ledger_path.exists() else None
    assert record.status == "dry_run"
    assert before_mtime == after_mtime
