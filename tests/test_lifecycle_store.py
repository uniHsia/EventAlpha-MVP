"""Tests for the JSON lifecycle store."""

from __future__ import annotations

from eventalpha.news import EventLifecycleStore, TrackedEvent
from eventalpha.schemas.base import utc_now


def test_lifecycle_store_load_save_upsert_list_active(tmp_path) -> None:
    """Store should round-trip tracked events through JSON."""
    path = tmp_path / "event_lifecycle_store.json"
    now = utc_now()
    event = TrackedEvent(
        canonical_title="AI chip export controls expand",
        first_seen_at=now,
        last_seen_at=now,
        sources=["Reuters"],
        source_count=1,
    )

    store = EventLifecycleStore(path)
    store.load()
    assert store.list_events() == []

    store.upsert(event)
    store.save()

    restored = EventLifecycleStore(path).load()
    assert restored.get(event.tracked_event_id).canonical_title == event.canonical_title
    assert len(restored.list_active_events()) == 1


def test_lifecycle_store_reset(tmp_path) -> None:
    """Reset should clear memory and remove persisted JSON."""
    path = tmp_path / "event_lifecycle_store.json"
    now = utc_now()
    store = EventLifecycleStore(path)
    store.upsert(TrackedEvent(canonical_title="Event", first_seen_at=now, last_seen_at=now))
    store.save()

    store.reset()

    assert store.list_events() == []
    assert not path.exists()
