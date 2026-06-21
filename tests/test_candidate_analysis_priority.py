"""Tests for priority-aware scheduler candidate analysis."""

from __future__ import annotations

from datetime import timedelta

from eventalpha.news import EventLifecycleStore, TrackedEvent
from eventalpha.scheduler import SchedulerJobConfig, SchedulerStateStore, run_candidate_analysis
from eventalpha.schemas.base import utc_now


def test_candidate_analysis_selects_top_priority_only(tmp_path) -> None:
    """Candidate analysis should pick top priority events, not just newest events."""
    lifecycle_path = tmp_path / "lifecycle.json"
    urgent, background = _seed_priority_events(lifecycle_path)
    store = _store(tmp_path)

    record = run_candidate_analysis(
        SchedulerJobConfig(job_id="candidate", job_type="candidate_analysis", dry_run=True, limit=1),
        store,
        lifecycle_store_path=lifecycle_path,
        pipeline_runner=_fail_pipeline,
    )

    notes = "\n".join(record.notes)
    assert record.status == "dry_run"
    assert record.candidate_items == 1
    assert urgent.canonical_title in notes
    assert f"Skipped background: {background.canonical_title}" in notes


def test_candidate_analysis_execute_skips_background_and_calls_pipeline_for_selected(tmp_path) -> None:
    """Execute mode should only call the pipeline for selectable priority events."""
    lifecycle_path = tmp_path / "lifecycle.json"
    urgent, background = _seed_priority_events(lifecycle_path)
    store = _store(tmp_path)
    calls = []

    def fake_pipeline(raw_news, **kwargs):
        calls.append(raw_news.title)
        return {"event_card": object()}

    record = run_candidate_analysis(
        SchedulerJobConfig(job_id="candidate", job_type="candidate_analysis", dry_run=False, limit=5),
        store,
        lifecycle_store_path=lifecycle_path,
        pipeline_runner=fake_pipeline,
    )

    assert record.status == "success"
    assert urgent.canonical_title in calls
    assert background.canonical_title not in calls


def _seed_priority_events(path) -> tuple[TrackedEvent, TrackedEvent]:
    now = utc_now()
    urgent = TrackedEvent(
        canonical_title="Official AI chip export control expands",
        lifecycle_stage="developing",
        first_seen_at=now - timedelta(hours=3),
        last_seen_at=now - timedelta(hours=1),
        source_count=4,
        sources=["Reuters", "Official Source", "AP", "Bloomberg"],
        credibility_status="high_confidence",
        official_evidence_status="official_source_present",
        dominant_keywords=["AI chip", "export control"],
    )
    background = TrackedEvent(
        canonical_title="Think tank commentary on old chip policy",
        lifecycle_stage="analysis_only",
        first_seen_at=now - timedelta(days=2),
        last_seen_at=now - timedelta(minutes=5),
        source_count=1,
        sources=["Think Tank Commentary"],
        credibility_status="single_source_low_confidence",
        dominant_keywords=["AI chip"],
    )
    store = EventLifecycleStore(path).load()
    store.upsert(background)
    store.upsert(urgent)
    store.save()
    return urgent, background


def _fail_pipeline(*args, **kwargs):
    raise AssertionError("pipeline should not be called during dry-run")


def _store(tmp_path) -> SchedulerStateStore:
    return SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
