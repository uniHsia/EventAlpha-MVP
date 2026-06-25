"""Shared schema types and constants."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


EventType = Literal[
    "ai_export_control",
    "geopolitical_conflict",
    "rate_policy",
    "trade_tariff",
    "earthquake_supply_chain",
    "unknown",
]
EventLevel = Literal["S", "A", "B", "C", "D"]
Direction = Literal["up", "down", "neutral", "mixed", "watch"]
Horizon = Literal["T+1", "T+3", "T+7"]
SpuriousRisk = Literal["low", "medium", "high"]
CausalValidity = Literal["valid", "partially_valid", "invalid", "unknown"]
ErrorType = Literal[
    "none",
    "source_error",
    "event_overestimated",
    "causal_chain_too_long",
    "spurious_mapping",
    "priced_in",
    "wrong_time_window",
    "wrong_asset_mapping",
    "macro_factor_override",
    "historical_analogy_error",
    "insufficient_evidence",
    "mixed_or_watch_only",
    "unknown",
]
SourceClassification = Literal[
    "official_source",
    "mainstream_media",
    "recognized_media",
    "social_media",
    "unknown_source",
]
ConclusionLevel = Literal[
    "fully_supported",
    "partially_supported",
    "direction_right_causality_unclear",
    "not_supported",
    "mixed",
]
VerificationStatus = Literal[
    "confirmed",
    "high_confidence",
    "needs_confirmation",
    "low_confidence",
    "rumor",
    "single_source_low_confidence",
    "official_single_source",
    "multi_source_observed",
    "analysis_only",
    "conflict_detected",
]
AssetType = Literal[
    "industry",
    "index",
    "etf",
    "theme",
    "commodity",
    "fx",
    "bond",
    "example_asset",
]

RISK_DISCLAIMER = (
    "本内容仅用于事件研究和市场分析，不构成投资建议。"
    "市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。"
)


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Create a readable local identifier."""
    return f"{prefix}_{uuid4().hex[:12]}"


class EventAlphaModel(BaseModel):
    """Base model for all EventAlpha schemas."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TimestampedModel(EventAlphaModel):
    """Base model with a creation timestamp."""

    created_at: datetime = Field(default_factory=utc_now)
