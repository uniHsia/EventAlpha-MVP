"""Tests for scheduler state store."""

from __future__ import annotations

from eventalpha.scheduler import SchedulerJobConfig, SchedulerRunRecord, SchedulerStateStore


def test_scheduler_state_store_config_roundtrip(tmp_path) -> None:
    """Config should save and load from JSON."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    config = SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", query="AI chips")

    assert store.load_config() == []
    store.save_config([config])
    loaded = store.load_config()

    assert len(loaded) == 1
    assert loaded[0].job_id == "scan"
    assert loaded[0].query == "AI chips"


def test_scheduler_state_store_append_recent_and_last_success(tmp_path) -> None:
    """Run records should append to JSONL and be queryable."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    failed = SchedulerRunRecord(job_id="scan", job_type="news_lifecycle_scan").finish("failed", errors=["boom"])
    success = SchedulerRunRecord(job_id="scan", job_type="news_lifecycle_scan").finish("success")
    status = SchedulerRunRecord(job_id="status", job_type="scheduler_status").finish("success")

    store.append_run(failed)
    store.append_run(success)
    store.append_run(status)

    recent = store.list_recent_runs(limit=2)
    assert [run.job_id for run in recent] == ["status", "scan"]
    last_success = store.get_last_successful_run("scan")
    assert last_success is not None
    assert last_success.run_id == success.run_id
    assert store.get_last_successful_run("missing") is None
