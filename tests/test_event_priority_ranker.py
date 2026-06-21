"""Tests for lifecycle event priority ranking."""

from __future__ import annotations

from datetime import timedelta

from eventalpha.news import TrackedEvent
from eventalpha.scheduler import EventPriorityRanker
from eventalpha.schemas.base import utc_now


def test_priority_ranker_sorts_official_multisource_before_commentary() -> None:
    """Official multi-source high-impact events should sort before commentary."""
    official = _event(
        title="Official tariff attack response raises geopolitical conflict risk",
        stage="developing",
        credibility="high_confidence",
        official="official_source_present",
        source_count=4,
        sources=["Reuters", "Official Ministry", "AP", "Bloomberg"],
        keywords=["tariff", "attack", "geopolitical"],
    )
    commentary = _event(
        title="Think tank commentary on possible tariff policy",
        stage="analysis_only",
        credibility="single_source_low_confidence",
        source_count=1,
        sources=["Think Tank Commentary"],
        keywords=["tariff"],
    )

    scores = EventPriorityRanker().rank([commentary, official])

    assert scores[0].tracked_event_id == official.tracked_event_id
    assert scores[0].urgency_score > scores[1].urgency_score


def test_priority_ranker_downranks_analysis_only() -> None:
    """Analysis-only events should be downranked to background."""
    event = _event(
        title="Research-only AI chip export control scenario",
        stage="analysis_only",
        credibility="high_confidence",
        official="official_source_present",
        source_count=4,
        keywords=["AI chip", "export control"],
    )

    score = EventPriorityRanker().score(event)

    assert score.urgency_level == "background"
    assert any("analysis_only" in penalty for penalty in score.penalties)


def test_priority_ranker_records_official_and_multisource_reasons() -> None:
    """Reasons should explain official and multi-source weight."""
    event = _event(
        title="Central bank rate decision confirmed",
        stage="developing",
        credibility="multi_source_supported",
        official="official_source_present",
        source_count=2,
        keywords=["rate"],
    )

    score = EventPriorityRanker().score(event)

    assert "multi-source supported credibility" in score.reasons
    assert "official source present" in score.reasons
    assert "source_count>=2" in score.reasons


def _event(
    *,
    title: str,
    stage: str,
    credibility: str,
    official: str | None = None,
    source_count: int = 1,
    sources: list[str] | None = None,
    keywords: list[str] | None = None,
) -> TrackedEvent:
    now = utc_now()
    return TrackedEvent(
        canonical_title=title,
        current_summary=title,
        lifecycle_stage=stage,
        first_seen_at=now - timedelta(hours=2),
        last_seen_at=now - timedelta(minutes=10),
        source_count=source_count,
        sources=sources or ["Reuters"],
        credibility_status=credibility,
        official_evidence_status=official,
        dominant_keywords=keywords or [],
    )
