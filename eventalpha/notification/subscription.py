"""Local subscriber configuration for the notification MVP."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel


class Subscriber(EventAlphaModel):
    """A local subscriber preference record."""

    subscriber_id: str
    channel: str = "wechat_placeholder"
    name: str | None = None
    keywords: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    min_priority: str = "A"
    enabled: bool = True


def load_subscribers(path: str | Path = "data/subscribers.demo.json") -> list[Subscriber]:
    """Load local subscriber preferences from JSON."""
    config_path = Path(path)
    if not config_path.exists():
        return []
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    rows = raw.get("subscribers", raw) if isinstance(raw, dict) else raw
    return [Subscriber(**row) for row in rows if isinstance(row, dict)]
