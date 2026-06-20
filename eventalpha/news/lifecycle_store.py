"""JSON-backed store for event lifecycle tracking."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eventalpha.schemas.base import utc_now

from .lifecycle import TrackedEvent


DEFAULT_LIFECYCLE_STORE_PATH = Path("data/event_lifecycle_store.json")


class EventLifecycleStore:
    """Persist tracked events in a small JSON file."""

    def __init__(self, path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH) -> None:
        self.path = Path(path)
        self.events: dict[str, TrackedEvent] = {}

    def load(self) -> "EventLifecycleStore":
        """Load events from JSON if the file exists."""
        if not self.path.exists():
            self.events = {}
            return self
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        events = raw.get("events", []) if isinstance(raw, dict) else []
        self.events = {
            event.tracked_event_id: event
            for event in (TrackedEvent.model_validate(item) for item in events)
        }
        return self

    def save(self) -> None:
        """Save tracked events to JSON."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "updated_at": utc_now().isoformat(),
            "events": [event.model_dump(mode="json") for event in self.list_events()],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, event: TrackedEvent) -> None:
        """Insert or replace one tracked event."""
        self.events[event.tracked_event_id] = event

    def get(self, tracked_event_id: str) -> TrackedEvent | None:
        """Return a tracked event by ID."""
        return self.events.get(tracked_event_id)

    def list_events(self) -> list[TrackedEvent]:
        """Return all tracked events sorted by recency."""
        return sorted(self.events.values(), key=lambda event: event.last_seen_at, reverse=True)

    def list_active_events(self) -> list[TrackedEvent]:
        """Return active tracked events sorted by recency."""
        return [event for event in self.list_events() if event.is_active]

    def reset(self) -> None:
        """Clear in-memory and persisted lifecycle state."""
        self.events = {}
        if self.path.exists():
            self.path.unlink()
