"""Tests for scheduler job runners."""

from __future__ import annotations

from eventalpha.news import EventLifecycleStore
from eventalpha.scheduler import (
    SchedulerJobConfig,
    SchedulerStateStore,
    run_candidate_analysis,
    run_news_lifecycle_scan,
    run_scheduler_status,
)


def test_news_lifecycle_scan_dry_run_does_not_save_store(tmp_path) -> None:
    """Dry-run lifecycle scan should process mock news without saving lifecycle state."""
    store = _store(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    config = SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", dry_run=True)

    record = run_news_lifecycle_scan(config, store, lifecycle_store_path=lifecycle_path)

    assert record.status == "dry_run"
    assert record.fetched_items > 0
    assert record.clusters_processed > 0
    assert record.lifecycle_updates > 0
    assert not lifecycle_path.exists()


def test_news_lifecycle_scan_execute_saves_lifecycle_store(tmp_path) -> None:
    """Execute mode may update the lifecycle JSON store but not ledger."""
    store = _store(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    config = SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", dry_run=False)

    record = run_news_lifecycle_scan(config, store, lifecycle_store_path=lifecycle_path)

    assert record.status == "success"
    assert lifecycle_path.exists()
    assert EventLifecycleStore(lifecycle_path).load().list_active_events()


def test_candidate_analysis_dry_run_reads_active_events_without_pipeline(tmp_path) -> None:
    """Candidate dry-run should not call pipeline."""
    store = _store(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    run_news_lifecycle_scan(
        SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", dry_run=False),
        store,
        lifecycle_store_path=lifecycle_path,
    )

    def fail_pipeline(*args, **kwargs):
        raise AssertionError("pipeline should not be called during dry-run")

    record = run_candidate_analysis(
        SchedulerJobConfig(job_id="candidate", job_type="candidate_analysis", dry_run=True, limit=2),
        store,
        lifecycle_store_path=lifecycle_path,
        pipeline_runner=fail_pipeline,
    )

    assert record.status == "dry_run"
    assert record.candidate_items == 2
    assert record.analyzed_events == 0


def test_candidate_analysis_execute_can_run_mock_pipeline(tmp_path) -> None:
    """Execute mode should call the supplied pipeline runner with persist config."""
    store = _store(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    run_news_lifecycle_scan(
        SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", dry_run=False),
        store,
        lifecycle_store_path=lifecycle_path,
    )
    calls = []

    def fake_pipeline(raw_news, **kwargs):
        calls.append((raw_news, kwargs))
        return {"event_card": object()}

    record = run_candidate_analysis(
        SchedulerJobConfig(job_id="candidate", job_type="candidate_analysis", dry_run=False, persist=False, limit=1),
        store,
        lifecycle_store_path=lifecycle_path,
        pipeline_runner=fake_pipeline,
    )

    assert record.status == "success"
    assert record.analyzed_events == 1
    assert calls
    assert calls[0][1]["persist"] is False


def test_scheduler_status_reports_state(tmp_path) -> None:
    """Status job should report config and recent runs without fetching."""
    store = _store(tmp_path)
    store.save_config([SchedulerJobConfig(job_id="status", job_type="scheduler_status")])

    record = run_scheduler_status(
        SchedulerJobConfig(job_id="status", job_type="scheduler_status"),
        store,
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
    )

    assert record.status == "success"
    assert any("Configured jobs: 1" in note for note in record.notes)


def _store(tmp_path) -> SchedulerStateStore:
    return SchedulerStateStore(tmp_path / "scheduler_state.json", tmp_path / "scheduler_runs.jsonl")
