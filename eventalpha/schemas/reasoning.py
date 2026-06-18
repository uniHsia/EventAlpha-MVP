"""Causal reasoning and anti-spurious check schemas."""

from __future__ import annotations

from pydantic import Field

from .base import Direction, Horizon, SpuriousRisk, TimestampedModel, new_id


class CausalStep(TimestampedModel):
    """One step in a causal chain."""

    order: int
    description: str
    variable_type: str = "market"
    evidence: str | None = None


class CausalChain(TimestampedModel):
    """Event-to-market causal reasoning chain."""

    chain_id: str = Field(default_factory=lambda: new_id("CHAIN"))
    event_id: str
    logic: list[CausalStep] = Field(default_factory=list)
    affected_assets: list[str] = Field(default_factory=list)
    direction: Direction = "mixed"
    time_horizon: Horizon = "T+3"
    confidence: float = 0.5
    rationale: str = ""


class AntiSpuriousCheck(TimestampedModel):
    """Result of checking over-extended or weak causal claims."""

    check_id: str = Field(default_factory=lambda: new_id("SPUR"))
    event_id: str
    chain_id: str
    spurious_risk: SpuriousRisk = "medium"
    issues: list[str] = Field(default_factory=list)
    required_verifications: list[str] = Field(default_factory=list)
    adjusted_confidence: float = 0.5
