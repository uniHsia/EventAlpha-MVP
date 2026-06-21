"""Tests for event urgency scores."""

from __future__ import annotations

from datetime import timedelta

from eventalpha.news import TrackedEvent
from eventalpha.scheduler import EventPriorityRanker, EventUrgencyScore
from eventalpha.schemas.base import utc_now


def test_event_urgency_score_clamps_score_and_derives_level() -> None:
    """Urgency scores should stay in 0..100 and derive labels."""
    high = EventUrgencyScore(tracked_event_id="TRACK_1", title="Event", urgency_score=150)
    low = EventUrgencyScore(tracked_event_id="TRACK_2", title="Event", urgency_score=-5)

    assert high.urgency_score == 100
    assert high.urgency_level == "urgent"
    assert low.urgency_score == 0
    assert low.urgency_level == "ignore"


def test_high_confidence_developing_event_ranks_high_or_urgent() -> None:
    """A fresh high-confidence multi-source event should rank at the top."""
    event = _event(
        title="US expands AI chip export control after official announcement",
        stage="developing",
        credibility="high_confidence",
        official="official_source_present",
        source_count=4,
        sources=["Reuters", "Commerce Department", "Bloomberg", "AP"],
        keywords=["AI chip", "export control"],
    )

    score = EventPriorityRanker().score(event)

    assert score.urgency_level in {"high", "urgent"}
    assert "high confidence credibility" in score.reasons


def test_analysis_only_is_capped_at_background() -> None:
    """Analysis-only events should not enter urgent tracking."""
    event = _event(
        title="Think tank analysis of AI chip policy",
        stage="analysis_only",
        credibility="high_confidence",
        official="official_source_present",
        source_count=4,
        sources=["Think Tank Research"],
        keywords=["AI chip", "export control"],
    )

    score = EventPriorityRanker().score(event)

    assert score.urgency_level == "background"
    assert any("analysis_only" in penalty for penalty in score.penalties)


def test_stale_is_capped_at_background() -> None:
    """Stale events should be capped below normal tracking urgency."""
    event = _event(
        title="Old tariff proposal remains unresolved",
        stage="stale",
        credibility="high_confidence",
        official="official_source_present",
        source_count=4,
        keywords=["tariff"],
        last_seen_delta=timedelta(days=10),
    )

    score = EventPriorityRanker().score(event)

    assert score.urgency_level in {"background", "ignore"}
    assert any("stale" in penalty for penalty in score.penalties)


def test_unconfirmed_or_considering_does_not_become_urgent() -> None:
    """Unconfirmed events should be capped at high even with strong keywords."""
    event = _event(
        title="Reports say export control may be under consideration",
        stage="unconfirmed_or_considering",
        credibility="unconfirmed_or_considering",
        official="official_source_present",
        source_count=4,
        keywords=["AI chip", "export control"],
    )

    score = EventPriorityRanker().score(event)

    assert score.urgency_level != "urgent"


def _event(
    *,
    title: str,
    stage: str,
    credibility: str,
    official: str | None = None,
    source_count: int = 1,
    sources: list[str] | None = None,
    keywords: list[str] | None = None,
    last_seen_delta: timedelta = timedelta(hours=1),
) -> TrackedEvent:
    now = utc_now()
    return TrackedEvent(
        canonical_title=title,
        current_summary=title,
        lifecycle_stage=stage,
        first_seen_at=now - timedelta(days=1),
        last_seen_at=now - last_seen_delta,
        source_count=source_count,
        sources=sources or ["Reuters"],
        credibility_status=credibility,
        official_evidence_status=official,
        dominant_keywords=keywords or [],
    )
