"""Tests for the urgent event scan scheduler job."""

from __future__ import annotations

from datetime import timedelta

from eventalpha.news import EventLifecycleStore, TrackedEvent
from eventalpha.scheduler import SchedulerJobConfig, SchedulerStateStore, run_urgent_event_scan
from eventalpha.schemas.base import utc_now


def test_urgent_event_scan_dry_run_does_not_save_policies(tmp_path) -> None:
    """Dry-run urgent scan should rank events without mutating scheduler policies."""
    lifecycle_path = tmp_path / "lifecycle.json"
    _seed_events(lifecycle_path)
    store = _store(tmp_path)

    record = run_urgent_event_scan(
        SchedulerJobConfig(job_id="urgent", job_type="urgent_event_scan", dry_run=True),
        store,
        lifecycle_store_path=lifecycle_path,
    )

    assert record.status == "dry_run"
    assert record.candidate_items == 3
    assert store.load_tracking_policies() == []
    assert any("Urgent events:" in note for note in record.notes)


def test_urgent_event_scan_execute_saves_policies(tmp_path) -> None:
    """Execute urgent scan should save tracking policies to scheduler state only."""
    lifecycle_path = tmp_path / "lifecycle.json"
    _seed_events(lifecycle_path)
    store = _store(tmp_path)

    record = run_urgent_event_scan(
        SchedulerJobConfig(job_id="urgent", job_type="urgent_event_scan", dry_run=False),
        store,
        lifecycle_store_path=lifecycle_path,
    )

    policies = store.load_tracking_policies()
    assert record.status == "success"
    assert len(policies) == 3
    assert any(policy.tracking_mode == "urgent" for policy in policies)
    assert any("Tracking policies saved" in note for note in record.notes)


def _seed_events(path) -> None:
    now = utc_now()
    lifecycle_store = EventLifecycleStore(path).load()
    lifecycle_store.upsert(
        TrackedEvent(
            canonical_title="Official AI chip export control expands",
            current_summary="Official AI chip export control expands.",
            lifecycle_stage="developing",
            first_seen_at=now - timedelta(hours=3),
            last_seen_at=now - timedelta(minutes=20),
            source_count=4,
            sources=["Reuters", "Official Source", "AP", "Bloomberg"],
            credibility_status="high_confidence",
            official_evidence_status="official_source_present",
            dominant_keywords=["AI chip", "export control"],
        )
    )
    lifecycle_store.upsert(
        TrackedEvent(
            canonical_title="Central bank rate policy update",
            lifecycle_stage="developing",
            first_seen_at=now - timedelta(hours=5),
            last_seen_at=now - timedelta(hours=2),
            source_count=2,
            sources=["Reuters", "Central Bank"],
            credibility_status="multi_source_supported",
            official_evidence_status="official_source_present",
            dominant_keywords=["rate"],
        )
    )
    lifecycle_store.upsert(
        TrackedEvent(
            canonical_title="Think tank commentary on chips",
            lifecycle_stage="analysis_only",
            first_seen_at=now - timedelta(hours=5),
            last_seen_at=now - timedelta(hours=1),
            source_count=1,
            sources=["Think Tank Commentary"],
            credibility_status="single_source_low_confidence",
            dominant_keywords=["AI chip"],
        )
    )
    lifecycle_store.save()


def _store(tmp_path) -> SchedulerStateStore:
    return SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
