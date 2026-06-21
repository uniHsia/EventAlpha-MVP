"""Tests for scheduler state store."""

from __future__ import annotations

from eventalpha.scheduler import SchedulerJobConfig, SchedulerRunRecord, SchedulerStateStore, TrackingPolicy


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


def test_scheduler_state_store_tracking_policy_roundtrip_preserves_config(tmp_path) -> None:
    """Tracking policies should save beside job config without overwriting it."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    config = SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan")
    policy = TrackingPolicy(
        tracked_event_id="TRACK_1",
        tracking_mode="urgent",
        scan_interval_minutes=15,
        analyze=True,
        reason="test",
    )

    store.save_config([config])
    store.save_tracking_policies([policy])

    assert store.load_config()[0].job_id == "scan"
    loaded = store.load_tracking_policies()
    assert len(loaded) == 1
    assert loaded[0].tracking_mode == "urgent"


def test_scheduler_state_store_skips_malformed_run_log_lines(tmp_path) -> None:
    """A malformed JSONL row should not break status reporting."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    success = SchedulerRunRecord(job_id="status", job_type="scheduler_status").finish("success")
    store.append_run(success)
    with (tmp_path / "runs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"run_id": "broken"\n')

    recent = store.list_recent_runs(limit=5)

    assert len(recent) == 1
    assert recent[0].run_id == success.run_id


def test_scheduler_state_store_treats_malformed_state_as_empty(tmp_path) -> None:
    """Malformed scheduler state should not prevent safe CLI recovery."""
    state_path = tmp_path / "state.json"
    state_path.write_text('{"jobs": []}\n{"broken": true}', encoding="utf-8")
    store = SchedulerStateStore(state_path, tmp_path / "runs.jsonl")

    assert store.load_config() == []
    assert store.load_tracking_policies() == []
