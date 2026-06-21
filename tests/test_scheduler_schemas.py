"""Tests for scheduler schemas."""

from __future__ import annotations

from eventalpha.scheduler import SchedulerJobConfig, SchedulerRunRecord


def test_scheduler_job_config_defaults_are_safe() -> None:
    """Scheduler config should default to offline dry-run behavior."""
    config = SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan")

    assert config.enabled is True
    assert config.interval_minutes == 60
    assert config.source == "rss"
    assert config.limit == 10
    assert config.real_fetch is False
    assert config.use_llm_extraction is False
    assert config.use_llm_causal is False
    assert config.use_llm_anti_spurious is False
    assert config.persist is False
    assert config.dry_run is True


def test_scheduler_job_config_custom_values() -> None:
    """Custom config values should be accepted and clamped where needed."""
    config = SchedulerJobConfig(
        job_id="candidate",
        job_type="candidate_analysis",
        interval_minutes=0,
        limit=0,
        dry_run=False,
    )

    assert config.interval_minutes == 1
    assert config.limit == 1
    assert config.dry_run is False


def test_scheduler_run_record_can_finish() -> None:
    """Run records should have generated IDs and supported statuses."""
    record = SchedulerRunRecord(job_id="status", job_type="scheduler_status")
    finished = record.finish("success", warnings=["careful"], notes=["ok"])

    assert record.run_id.startswith("SCHED_RUN_")
    assert record.status == "started"
    assert finished.status == "success"
    assert finished.finished_at is not None
    assert finished.warnings == ["careful"]
    assert finished.notes == ["ok"]


def test_scheduler_job_config_accepts_urgent_scan() -> None:
    """Urgent event scan should be a supported scheduler job type."""
    config = SchedulerJobConfig(job_id="urgent", job_type="urgent_event_scan")

    assert config.job_type == "urgent_event_scan"
