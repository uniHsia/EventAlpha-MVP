"""Tests for trade tariff alert scoring calibration."""

from __future__ import annotations

from eventalpha.agents.scoring import score_event
from eventalpha.schemas import EventVerification, StructuredEvent


def test_announced_tariff_escalation_forces_level_a_alert() -> None:
    """Announced tariff escalation should not be downgraded below alert level."""
    event = StructuredEvent(
        event_type="trade_tariff",
        event_title="美国宣布对部分进口商品加征关税",
        summary="美国发布新关税政策，涉及进口商品和贸易壁垒。",
        status="announced",
        entities=["美国", "加征关税", "进口商品"],
        affected_industries=["出口链"],
        affected_assets_hint=["出口链"],
        novelty_score=0.4,
    )
    verification = EventVerification(event_id=event.event_id, credibility_score=0.4)

    score = score_event(event, verification)

    assert score.impact_score >= 70
    assert score.event_level == "A"
    assert score.trigger_alert is True
    assert score.tracking_mode == "enhanced"
    assert score.score_breakdown["trade_tariff_alert_floor"] > 0


def test_trade_negotiation_rumor_is_not_forced_to_alert() -> None:
    """Rumor-stage tariff talks should not receive the announced-event floor."""
    event = StructuredEvent(
        event_type="trade_tariff",
        event_title="两国恢复贸易谈判，关税调整尚未落地",
        summary="市场关注谈判结果，但政策尚未确认。",
        status="rumor",
        entities=["贸易", "关税"],
        affected_industries=["出口链"],
        affected_assets_hint=["出口链"],
        novelty_score=0.4,
    )
    verification = EventVerification(event_id=event.event_id, credibility_score=0.4)

    score = score_event(event, verification)

    assert score.event_level == "B"
    assert score.trigger_alert is False
    assert "trade_tariff_alert_floor" not in score.score_breakdown
