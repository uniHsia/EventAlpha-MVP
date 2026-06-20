"""Tests for lifecycle tracking schemas."""

from __future__ import annotations

from eventalpha.news import (
    EventLifecycleUpdate,
    EventMatchResult,
    EventTimelineEntry,
    TrackedEvent,
    make_event_key,
    make_tracked_event_id,
)
from eventalpha.schemas.base import utc_now


def test_lifecycle_schemas_roundtrip() -> None:
    """Lifecycle schemas should be creatable and JSON round-trippable."""
    now = utc_now()
    entry = EventTimelineEntry(
        timestamp=now,
        update_type="new_event",
        cluster_id="CLUSTER_1",
        title="AI chip export controls expand",
        source_count=1,
        credibility_status="single_source_low_confidence",
        official_evidence_status="no_official_evidence",
    )
    event_key = make_event_key("AI chip export controls expand", ["technology", "export"])
    event = TrackedEvent(
        event_key=event_key,
        tracked_event_id=make_tracked_event_id(event_key),
        canonical_title="AI chip export controls expand",
        first_seen_at=now,
        last_seen_at=now,
        cluster_ids=["CLUSTER_1"],
        sources=["Reuters"],
        source_count=1,
        timeline=[entry],
    )
    update = EventLifecycleUpdate(
        tracked_event_id=event.tracked_event_id,
        update_type="new_event",
        new_stage="new",
    )
    match = EventMatchResult(matched=True, tracked_event_id=event.tracked_event_id, score=0.9)

    restored = TrackedEvent.model_validate(event.model_dump(mode="json"))

    assert restored.tracked_event_id == event.tracked_event_id
    assert restored.timeline[0].update_type == "new_event"
    assert update.update_type == "new_event"
    assert match.matched is True
