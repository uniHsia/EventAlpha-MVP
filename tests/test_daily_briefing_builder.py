"""Tests for daily briefing builder behavior."""

from __future__ import annotations

from datetime import date, timedelta

from eventalpha.briefing import BriefingCollectedData, DailyBriefingBuilder
from eventalpha.news import TrackedEvent
from eventalpha.scheduler import EventPriorityRanker, SchedulerRunRecord
from eventalpha.schemas.base import utc_now


def test_builder_sections_priority_and_demo_notes() -> None:
    """Builder should create all sections and keep background out of重点事件."""
    now = utc_now()
    urgent = TrackedEvent(
        canonical_title="AI chip export control confirmed",
        current_summary="Official multi-source export control update.",
        lifecycle_stage="developing",
        first_seen_at=now - timedelta(hours=1),
        last_seen_at=now,
        source_count=4,
        sources=["official", "wire"],
        credibility_status="high_confidence",
        official_evidence_status="official_source_present",
        dominant_keywords=["AI chip", "export control"],
    )
    background = TrackedEvent(
        canonical_title="Research commentary on supply chains",
        lifecycle_stage="analysis_only",
        first_seen_at=now - timedelta(days=2),
        last_seen_at=now - timedelta(days=2),
        source_count=1,
        sources=["think tank"],
        credibility_status="analysis_only",
        dominant_keywords=["commentary"],
    )
    scores = EventPriorityRanker().rank([urgent, background])
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        active_events=[urgent, background],
        urgency_scores=scores,
        event_cards=[
            {
                "card_id": "CARD_1",
                "event_id": "EVT_1",
                "event_title": "AI card",
                "event_level": "A",
                "one_sentence": "summary",
                "risk_factors": ["historical demo signals are illustrative"],
                "verification_indicators": ["verify official filing"],
            }
        ],
        review_results=[
            {
                "review_id": "REV_1",
                "prediction_id": "PRED_1",
                "event_id": "EVT_1",
                "horizon": "T+1",
                "asset_name": "AI ETF",
                "direction_correct": 1,
                "excess_return": 0.01,
                "causal_validity": "valid",
                "review_conclusion": "supported",
                "error_type": "none",
            }
        ],
        rule_updates=[
            {
                "update_id": "RULE_1",
                "rule_id": "RULE_AI",
                "prediction_id": "PRED_1",
                "old_weight": 0.5,
                "new_weight": 0.55,
                "reason": "review-backed adjustment",
                "update_action": "increase",
            }
        ],
        recent_runs=[
            SchedulerRunRecord(
                job_id="auto_review_runner",
                job_type="auto_review_runner",
                status="success",
                candidate_items=1,
                analyzed_events=1,
                notes=["ReviewResult count: 5.", "RuleUpdate count: 1."],
            ).finish("success")
        ],
    )

    briefing = DailyBriefingBuilder(max_items=5).build(data)
    sections = {section.section_id: section for section in briefing.sections}

    assert set(sections) == {
        "new_events",
        "urgent_events",
        "lifecycle_updates",
        "event_cards",
        "history_validation",
        "auto_reviews",
        "rule_updates",
        "tomorrow_watchlist",
        "system_status",
    }
    assert sections["new_events"].items[0].title == urgent.canonical_title
    assert all(item.title != background.canonical_title for item in sections["new_events"].items)
    assert sections["history_validation"].items[0].priority == "demo_only"
    assert any("ReviewResult count" in note for note in sections["auto_reviews"].notes)
