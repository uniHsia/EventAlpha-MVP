"""Tests for APScheduler wrapper registration."""

from __future__ import annotations

from eventalpha.scheduler import EventAlphaAPScheduler, SchedulerJobConfig, SchedulerStateStore


def test_apscheduler_runner_registers_enabled_jobs_only(tmp_path) -> None:
    """APScheduler wrapper should register interval jobs without waiting."""
    configs = [
        SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", interval_minutes=5),
        SchedulerJobConfig(job_id="candidate", job_type="candidate_analysis", enabled=False),
    ]
    runner = EventAlphaAPScheduler(
        configs,
        store=SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl"),
    )

    runner.register_jobs()

    assert runner.list_registered_job_ids() == ["scan"]
    job = runner.scheduler.get_job("scan")
    assert job is not None
    assert str(job.trigger).startswith("interval")
