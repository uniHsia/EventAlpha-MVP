"""Asset proxy mapping schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import Direction, EventAlphaModel


AssetProvider = Literal["mock", "csv", "akshare", "manual", "missing"]
MappingStatus = Literal["verified", "candidate", "unverified", "missing"]
ValidationStatus = Literal["not_checked", "live_ok", "live_failed", "cache_only"]


class AssetProxyCandidate(EventAlphaModel):
    """One candidate proxy asset for reviewing a predicted asset."""

    event_type: str
    asset_name: str
    proxy_asset_name: str
    provider: AssetProvider = "missing"
    provider_type: str | None = None
    provider_symbol: str | None = None
    asset_type: str = "theme"
    benchmark: str | None = None
    direction: Direction = "watch"
    relation: str = "watch"
    confidence: float = 0.5
    mapping_status: MappingStatus = "candidate"
    validation_status: ValidationStatus = "not_checked"
    last_checked_at: str | None = None
    last_error: str | None = None
    min_price_points: int | None = None
    fallback_rank: int = 0
    rationale: str = ""
    verification_notes: list[str] = Field(default_factory=list)


class AssetProxyRule(EventAlphaModel):
    """Event-specific proxy mapping rule."""

    event_type: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    candidates: list[AssetProxyCandidate] = Field(default_factory=list)


class ProviderRoute(EventAlphaModel):
    """Resolved provider route for one asset review request."""

    asset_name: str
    proxy_asset_name: str
    provider: AssetProvider
    provider_type: str | None = None
    provider_symbol: str | None = None
    asset_type: str = "theme"
    benchmark: str | None = None
    direction: Direction = "watch"
    relation: str = "watch"
    confidence: float = 0.5
    mapping_status: MappingStatus = "missing"
    validation_status: ValidationStatus = "not_checked"
    last_checked_at: str | None = None
    last_error: str | None = None
    min_price_points: int | None = None
    fallback_rank: int = 0
    event_type: str | None = None
    route_source: Literal["event_proxy", "asset_code", "missing"] = "missing"
    is_usable: bool = False
    reason: str = ""


class AssetCoverageStatus(EventAlphaModel):
    """Coverage status for one predicted asset."""

    event_type: str | None = None
    asset_name: str
    proxy_asset_name: str | None = None
    provider: AssetProvider = "missing"
    mapping_status: MappingStatus = "missing"
    validation_status: ValidationStatus = "not_checked"
    route_source: Literal["event_proxy", "asset_code", "missing"] = "missing"
    fallback_available: bool = False
    fallback_routes: list[ProviderRoute] = Field(default_factory=list)
    is_usable: bool = False
    reason: str = ""
