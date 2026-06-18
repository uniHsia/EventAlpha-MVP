"""Market mapping schemas."""

from __future__ import annotations

from pydantic import Field

from .base import AssetType, Direction, TimestampedModel, new_id


class MappedAsset(TimestampedModel):
    """Mapped market object for research observation."""

    asset_name: str
    asset_type: AssetType = "theme"
    direction: Direction = "mixed"
    relation: str = "watch"
    rationale: str = ""
    benchmark: str = "沪深300"
    confidence: float = 0.5


class MarketMapping(TimestampedModel):
    """Event-to-market mapping result."""

    mapping_id: str = Field(default_factory=lambda: new_id("MAP"))
    event_id: str
    mapped_assets: list[MappedAsset] = Field(default_factory=list)
    watch_indicators: list[str] = Field(default_factory=list)
    mapping_notes: str = ""
