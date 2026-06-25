"""Schemas for news source collection."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from pydantic import Field, model_validator

from eventalpha.schemas.base import EventAlphaModel, new_id, utc_now


def make_news_id(
    title: str,
    source: str,
    url: str | None = None,
) -> str:
    """Generate a stable news identifier from URL or source/title."""
    key = _normalize_url(url) if url else ""
    if not key:
        key = f"{_normalize_text(source)}::{_normalize_text(title)}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"NEWS_{digest}"


def make_cluster_id(items: list["NewsItem"]) -> str:
    """Generate a stable cluster identifier from sorted news IDs."""
    key = "::".join(sorted(item.news_id for item in items))
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"CLUSTER_{digest}"


def make_claim_id(claim_text: str, supporting_item_ids: list[str]) -> str:
    """Generate a stable claim identifier from normalized text and item IDs."""
    key = f"{_normalize_text(claim_text)}::{'::'.join(sorted(supporting_item_ids))}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"CLAIM_{digest}"


class NewsItem(EventAlphaModel):
    """Standardized candidate news item from an external source."""

    news_id: str = ""
    title: str
    summary: str | None = None
    url: str | None = None
    source: str
    source_type: str = "unknown"
    published_at: datetime | None = None
    language: str | None = None
    country: str | None = None
    raw_text: str | None = None
    tags: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def fill_news_id(self) -> "NewsItem":
        """Create a stable ID when providers do not supply one."""
        if not self.news_id:
            self.news_id = make_news_id(
                title=self.title,
                source=self.source,
                url=self.url,
            )
        return self


class NewsFetchResult(EventAlphaModel):
    """Result from one news provider fetch."""

    source_name: str
    fetched_at: datetime = Field(default_factory=utc_now)
    items: list[NewsItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SourceRegistryEntry(EventAlphaModel):
    """Metadata for one configured external news source."""

    source_name: str
    source_type: str
    enabled: bool = True
    region: str | None = None
    language: str | None = None
    credibility_base: float = 0.5
    fetch_mode: str = "unknown"
    notes: str | None = None


class SourceCheckRun(EventAlphaModel):
    """One fetch/check attempt for a configured source."""

    check_run_id: str = Field(default_factory=lambda: new_id("SRCCHK"))
    source_run_id: str
    source_name: str
    query: str | None = None
    status: str = "not_checked"
    fetched_at: datetime = Field(default_factory=utc_now)
    item_count: int = 0
    error_text: str | None = None
    raw_result_notes: str | None = None


class RawNewsItemRecord(EventAlphaModel):
    """One fetched external item before deduplication or clustering."""

    collected_item_id: str = Field(default_factory=lambda: new_id("RAWITEM"))
    source_run_id: str
    news_id: str
    title: str
    summary: str | None = None
    url: str | None = None
    source: str
    source_type: str = "unknown"
    published_at: datetime | None = None
    language: str | None = None
    country: str | None = None
    raw_text: str | None = None
    tags: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=utc_now)
    query: str | None = None
    is_duplicate: bool = False


class EventCluster(EventAlphaModel):
    """Lightweight event cluster built from related news items."""

    cluster_id: str = ""
    canonical_title: str
    canonical_summary: str | None = None
    items: list[NewsItem]
    sources: list[str] = Field(default_factory=list)
    source_count: int = 0
    item_count: int = 0
    unique_source_count: int = 0
    mainstream_source_count: int = 0
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    dominant_keywords: list[str] = Field(default_factory=list)
    candidate_event_type: str | None = None
    cluster_type: str = "single_news_event"
    independent_confirmation: bool = False
    verification_status: str = "single_source"
    confidence: float = 0.0
    debug_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_cluster_fields(self) -> "EventCluster":
        """Fill derived cluster fields from items."""
        if not self.cluster_id:
            self.cluster_id = make_cluster_id(self.items)
        if not self.sources:
            self.sources = _unique(item.source for item in self.items)
        self.item_count = len(self.items)
        self.unique_source_count = len(set(self.sources))
        self.source_count = self.unique_source_count
        if self.first_seen_at is None or self.last_seen_at is None:
            seen_at = [
                item.published_at or item.fetched_at
                for item in self.items
                if item.published_at or item.fetched_at
            ]
            if seen_at:
                self.first_seen_at = self.first_seen_at or min(seen_at)
                self.last_seen_at = self.last_seen_at or max(seen_at)
        if not self.independent_confirmation:
            self.independent_confirmation = (
                self.unique_source_count >= 2
                and self.cluster_type in {"multi_source_event", "official_update_cluster"}
            )
        return self


class SourceCredibility(EventAlphaModel):
    """Credibility classification for a news source."""

    source_name: str
    source_type: str = "blog_or_unknown"
    credibility_tier: str = "unknown"
    rationale: str = ""


class ClusterClaim(EventAlphaModel):
    """A lightweight claim extracted from an EventCluster."""

    claim_id: str = ""
    claim_text: str
    claim_type: str = "event_fact"
    supporting_item_ids: list[str] = Field(default_factory=list)
    supporting_sources: list[str] = Field(default_factory=list)
    contradicting_item_ids: list[str] = Field(default_factory=list)
    uncertainty_markers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_claim_id(self) -> "ClusterClaim":
        """Fill a stable claim ID when not provided."""
        if not self.claim_id:
            self.claim_id = make_claim_id(self.claim_text, self.supporting_item_ids)
        return self


class ClaimConsistencySummary(EventAlphaModel):
    """Summary of cross-source claim consistency."""

    status: str
    supporting_source_count: int = 0
    high_credibility_source_count: int = 0
    uncertainty_count: int = 0
    analysis_only: bool = False
    rationale: str = ""


class ClusterCredibilityReport(EventAlphaModel):
    """Cluster-level pre-verification credibility report."""

    cluster_id: str
    credibility_score: float
    credibility_status: str
    source_summary: list[SourceCredibility] = Field(default_factory=list)
    claims: list[ClusterClaim] = Field(default_factory=list)
    consistency_status: str
    official_evidence_status: str
    risk_flags: list[str] = Field(default_factory=list)
    verification_notes: list[str] = Field(default_factory=list)


class EventClusterRecord(EventAlphaModel):
    """Persisted cluster row bound to one source run."""

    cluster_record_id: str = Field(default_factory=lambda: new_id("CLSTR"))
    source_run_id: str
    cluster_id: str
    canonical_title: str
    canonical_summary: str | None = None
    source_count: int = 0
    item_count: int = 0
    unique_source_count: int = 0
    mainstream_source_count: int = 0
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    dominant_keywords: list[str] = Field(default_factory=list)
    candidate_event_type: str | None = None
    cluster_type: str = "single_news_event"
    independent_confirmation: bool = False
    verification_status: str = "single_source"
    confidence: float = 0.0
    debug_reasons: list[str] = Field(default_factory=list)


class CredibilityEvidence(EventAlphaModel):
    """Persisted credibility/evidence annotation for one cluster or event."""

    evidence_record_id: str = Field(default_factory=lambda: new_id("EVID"))
    source_run_id: str | None = None
    cluster_id: str | None = None
    event_id: str | None = None
    evidence_key: str
    source_name: str | None = None
    evidence_type: str
    claim_text: str
    supporting_item_ids: list[str] = Field(default_factory=list)
    supporting_sources: list[str] = Field(default_factory=list)
    consistency_status: str | None = None
    official_evidence_status: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    note_text: str | None = None


class SourceCredibilityState(EventAlphaModel):
    """Persisted baseline credibility state for one source."""

    source_name: str
    source_type: str = "unknown"
    credibility_tier: str = "unknown"
    historical_accuracy: float | None = None
    weight: float = 0.5
    last_verified_at: datetime | None = None
    notes: str | None = None


def _normalize_url(url: str | None) -> str:
    if not url:
        return ""
    return str(url).strip().rstrip("/").casefold()


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
