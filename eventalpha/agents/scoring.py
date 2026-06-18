"""Rule-based mock impact scoring agent."""

from __future__ import annotations

from eventalpha.schemas import EventVerification, ImpactScore, StructuredEvent


EVENT_TYPE_WEIGHTS = {
    "ai_export_control": 35,
    "geopolitical_conflict": 40,
    "rate_policy": 38,
    "trade_tariff": 34,
    "earthquake_supply_chain": 24,
    "unknown": 8,
}


def score_event(event: StructuredEvent, verification: EventVerification) -> ImpactScore:
    """Score event impact with simple deterministic weights."""
    credibility = int(verification.credibility_score * 20)
    event_weight = EVENT_TYPE_WEIGHTS.get(event.event_type, 8)
    novelty = int(event.novelty_score * 10)
    tradability = 10 if event.affected_assets_hint else 3
    scope = 10 if len(event.affected_industries) >= 3 else 5

    total = min(100, credibility + event_weight + novelty + tradability + scope)
    if total >= 85:
        level = "S"
        tracking_mode = "urgent"
    elif total >= 70:
        level = "A"
        tracking_mode = "enhanced"
    elif total >= 55:
        level = "B"
        tracking_mode = "normal"
    elif total >= 40:
        level = "C"
        tracking_mode = "low"
    else:
        level = "D"
        tracking_mode = "none"

    return ImpactScore(
        event_id=event.event_id,
        impact_score=total,
        event_level=level,
        trigger_alert=level in {"S", "A"},
        tracking_mode=tracking_mode,
        score_breakdown={
            "credibility": credibility,
            "event_type": event_weight,
            "novelty": novelty,
            "tradability": tradability,
            "scope": scope,
        },
    )
