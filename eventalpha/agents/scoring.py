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
    score_breakdown = {
        "credibility": credibility,
        "event_type": event_weight,
        "novelty": novelty,
        "tradability": tradability,
        "scope": scope,
    }
    if _requires_trade_tariff_alert_floor(event) and total < 70:
        score_breakdown["trade_tariff_alert_floor"] = 70 - total
        total = 70

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
        score_breakdown=score_breakdown,
    )


def _requires_trade_tariff_alert_floor(event: StructuredEvent) -> bool:
    """Force announced tariff escalation events to at least level A."""
    if event.event_type != "trade_tariff" or event.status != "announced":
        return False
    text = " ".join(
        [
            event.event_title,
            event.summary,
            *event.entities,
            *event.affected_industries,
            *event.affected_assets_hint,
        ]
    )
    tariff_escalation_keywords = [
        "加征关税",
        "关税上调",
        "进口商品",
        "贸易壁垒",
        "提高关税",
    ]
    return any(keyword in text for keyword in tariff_escalation_keywords)
