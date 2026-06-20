"""Schemas and helpers for event lifecycle tracking."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from pydantic import Field, model_validator

from eventalpha.schemas.base import EventAlphaModel, utc_now

from .schemas import ClusterCredibilityReport, EventCluster


def make_event_key(title: str, dominant_keywords: list[str] | None = None) -> str:
    """Create a stable event key from normalized title and dominant keywords."""
    keyword_part = "::".join(sorted(_normalize_text(keyword) for keyword in dominant_keywords or [] if keyword))
    key = f"{_normalize_text(title)}::{keyword_part}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"EVENTKEY_{digest}"


def make_tracked_event_id(event_key: str) -> str:
    """Create a stable tracked-event identifier from an event key."""
    digest = hashlib.sha256(event_key.encode("utf-8")).hexdigest()[:16]
    return f"TRACK_{digest}"


class EventTimelineEntry(EventAlphaModel):
    """One lifecycle timeline entry for a tracked event."""

    timestamp: datetime = Field(default_factory=utc_now)
    update_type: str
    cluster_id: str | None = None
    title: str | None = None
    summary: str | None = None
    source_count: int | None = None
    credibility_status: str | None = None
    official_evidence_status: str | None = None
    notes: list[str] = Field(default_factory=list)


class TrackedEvent(EventAlphaModel):
    """Persistent lifecycle state for an event across clusters."""

    tracked_event_id: str = ""
    event_key: str = ""
    canonical_title: str
    current_summary: str | None = None
    lifecycle_stage: str = "new"
    first_seen_at: datetime
    last_seen_at: datetime
    cluster_ids: list[str] = Field(default_factory=list)
    source_count: int = 0
    sources: list[str] = Field(default_factory=list)
    credibility_status: str | None = None
    official_evidence_status: str | None = None
    latest_claims: list[str] = Field(default_factory=list)
    dominant_keywords: list[str] = Field(default_factory=list)
    timeline: list[EventTimelineEntry] = Field(default_factory=list)
    is_active: bool = True

    @model_validator(mode="after")
    def fill_ids(self) -> "TrackedEvent":
        """Fill stable lifecycle identifiers when omitted."""
        if not self.event_key:
            self.event_key = make_event_key(self.canonical_title, self.dominant_keywords)
        if not self.tracked_event_id:
            self.tracked_event_id = make_tracked_event_id(self.event_key)
        self.cluster_ids = _unique(self.cluster_ids)
        self.sources = _unique(self.sources)
        self.dominant_keywords = _unique(self.dominant_keywords)
        self.latest_claims = _unique(self.latest_claims)
        if self.source_count < len(self.sources):
            self.source_count = len(self.sources)
        return self


class EventLifecycleUpdate(EventAlphaModel):
    """A structured lifecycle update emitted by the updater."""

    tracked_event_id: str
    update_type: str
    old_stage: str | None = None
    new_stage: str | None = None
    cluster_id: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EventMatchResult(EventAlphaModel):
    """Result of matching a cluster to existing tracked events."""

    matched: bool
    tracked_event_id: str | None = None
    score: float = 0.0
    reason: str = ""


def tracked_event_from_cluster(
    cluster: EventCluster,
    credibility_report: ClusterCredibilityReport,
    now: datetime | None = None,
) -> TrackedEvent:
    """Create a new TrackedEvent from a cluster and credibility report."""
    timestamp = now or utc_now()
    stage = stage_from_credibility(credibility_report.credibility_status)
    claims = [claim.claim_text for claim in credibility_report.claims]
    event = TrackedEvent(
        canonical_title=cluster.canonical_title,
        current_summary=cluster.canonical_summary,
        lifecycle_stage=stage,
        first_seen_at=timestamp,
        last_seen_at=timestamp,
        cluster_ids=[cluster.cluster_id],
        source_count=cluster.source_count,
        sources=cluster.sources,
        credibility_status=credibility_report.credibility_status,
        official_evidence_status=credibility_report.official_evidence_status,
        latest_claims=claims,
        dominant_keywords=cluster.dominant_keywords,
        timeline=[
            EventTimelineEntry(
                timestamp=timestamp,
                update_type="new_event",
                cluster_id=cluster.cluster_id,
                title=cluster.canonical_title,
                summary=cluster.canonical_summary,
                source_count=cluster.source_count,
                credibility_status=credibility_report.credibility_status,
                official_evidence_status=credibility_report.official_evidence_status,
                notes=[f"Initial lifecycle stage: {stage}."],
            )
        ],
    )
    return event


def stage_from_credibility(credibility_status: str | None) -> str:
    """Map cluster credibility status into lifecycle stage."""
    if credibility_status == "analysis_only":
        return "analysis_only"
    if credibility_status == "conflicting_claims":
        return "conflicting"
    if credibility_status == "unconfirmed_or_considering":
        return "unconfirmed_or_considering"
    if credibility_status == "high_confidence":
        return "confirmed"
    return "new"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _unique(values) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
