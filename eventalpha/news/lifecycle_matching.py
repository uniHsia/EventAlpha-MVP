"""Rule-based matching from new clusters to tracked lifecycle events."""

from __future__ import annotations

import re
from datetime import datetime

from .clustering import jaccard
from .lifecycle import EventMatchResult, TrackedEvent
from .schemas import ClusterCredibilityReport, EventCluster


STOPWORDS = {
    "about",
    "after",
    "against",
    "and",
    "are",
    "china",
    "chinese",
    "for",
    "from",
    "has",
    "into",
    "its",
    "new",
    "news",
    "over",
    "says",
    "the",
    "that",
    "this",
    "to",
    "us",
    "with",
}


class EventLifecycleMatcher:
    """Match incoming event clusters against existing tracked events."""

    def __init__(self, similarity_threshold: float = 0.42) -> None:
        self.similarity_threshold = similarity_threshold

    def match(
        self,
        cluster: EventCluster,
        credibility_report: ClusterCredibilityReport,
        existing_events: list[TrackedEvent],
    ) -> EventMatchResult:
        """Return the best matching tracked event for a cluster."""
        for event in existing_events:
            if cluster.cluster_id in event.cluster_ids:
                return EventMatchResult(
                    matched=True,
                    tracked_event_id=event.tracked_event_id,
                    score=1.0,
                    reason=f"cluster_id match: {cluster.cluster_id}",
                )

        best_event: TrackedEvent | None = None
        best_score = 0.0
        best_reason = ""
        for event in existing_events:
            score, reason = self._score(cluster, credibility_report, event)
            if score > best_score:
                best_event = event
                best_score = score
                best_reason = reason

        if best_event and best_score >= self.similarity_threshold:
            return EventMatchResult(
                matched=True,
                tracked_event_id=best_event.tracked_event_id,
                score=round(best_score, 4),
                reason=best_reason,
            )
        return EventMatchResult(
            matched=False,
            tracked_event_id=None,
            score=round(best_score, 4),
            reason=best_reason or "no existing event passed similarity threshold",
        )

    def _score(
        self,
        cluster: EventCluster,
        credibility_report: ClusterCredibilityReport,
        event: TrackedEvent,
    ) -> tuple[float, str]:
        title_score = jaccard(_tokens(cluster.canonical_title), _tokens(event.canonical_title))
        keyword_score = jaccard(set(cluster.dominant_keywords), set(event.dominant_keywords))
        claim_score = _claim_overlap(credibility_report, event)
        combined = (title_score * 0.45) + (keyword_score * 0.20) + (claim_score * 0.35)
        score = max(combined, title_score * 0.92, claim_score * 0.92)
        score *= _time_factor(cluster.last_seen_at, event.last_seen_at)

        analysis_mismatch = (
            credibility_report.credibility_status == "analysis_only" and event.lifecycle_stage != "analysis_only"
        ) or (
            credibility_report.credibility_status != "analysis_only" and event.lifecycle_stage == "analysis_only"
        )
        if analysis_mismatch and score < 0.75:
            return (
                score * 0.5,
                "analysis_only/factual mismatch reduced match confidence",
            )

        reason = (
            f"title={title_score:.2f}, keywords={keyword_score:.2f}, "
            f"claims={claim_score:.2f}, time_factor={_time_factor(cluster.last_seen_at, event.last_seen_at):.2f}"
        )
        return score, reason


def _claim_overlap(report: ClusterCredibilityReport, event: TrackedEvent) -> float:
    if not report.claims or not event.latest_claims:
        return 0.0
    scores = [
        jaccard(_tokens(claim.claim_text), _tokens(existing_claim))
        for claim in report.claims
        for existing_claim in event.latest_claims
    ]
    return max(scores or [0.0])


def _time_factor(cluster_time: datetime | None, event_time: datetime | None) -> float:
    if not cluster_time or not event_time:
        return 1.0
    days = abs((cluster_time - event_time).days)
    if days > 45:
        return 0.55
    if days > 14:
        return 0.85
    return 1.0


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.casefold())
        if len(token) >= 3 and token not in STOPWORDS
    }
