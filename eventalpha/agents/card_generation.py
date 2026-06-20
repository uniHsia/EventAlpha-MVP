"""Mock event card generation agent."""

from __future__ import annotations

from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    EventCard,
    EventVerification,
    ImpactScore,
    MarketMapping,
    RawNews,
    StructuredEvent,
)
from eventalpha.services import CritiqueCompressionService


_critique_service = CritiqueCompressionService()


def _impact_text(asset_name: str, direction: str, final_confidence: float) -> str:
    confidence_text = f"final_confidence={final_confidence:.2f}"
    if direction == "up":
        return f"{asset_name}: possible upside or stronger market attention ({confidence_text})"
    if direction == "down":
        return f"{asset_name}: possible pressure ({confidence_text})"
    return f"{asset_name}: needs observation ({confidence_text})"


def generate_event_card(
    raw_news: RawNews,
    event: StructuredEvent,
    verification: EventVerification,
    score: ImpactScore,
    chain: CausalChain,
    anti_spurious: AntiSpuriousCheck,
    mapping: MarketMapping,
) -> EventCard:
    """Create a user-facing research card from structured outputs."""
    possible_impacts = [
        _impact_text(
            asset.asset_name,
            asset.direction,
            round(asset.confidence * anti_spurious.adjusted_confidence, 4),
        )
        for asset in mapping.mapped_assets
    ]
    risk_factors = _critique_service.compact_event_card_risk_factors(
        risk_flags=list(verification.risk_flags),
        anti_spurious_issues=list(anti_spurious.issues),
        limit=6,
    )
    if not risk_factors:
        risk_factors = ["The market may already have priced in part of the event."]

    verification_indicators = _critique_service.compact_event_card_verification_indicators(
        watch_indicators=list(mapping.watch_indicators),
        required_verifications=list(anti_spurious.required_verifications),
        limit=8,
    )

    industries = ", ".join(event.affected_industries[:3]) or "related markets"
    return EventCard(
        event_id=event.event_id,
        event_title=event.event_title,
        event_level=score.event_level,
        credibility_score=verification.credibility_score,
        one_sentence=(
            f"{event.event_title} may affect {industries}; "
            "follow-up market data is still needed for verification."
        ),
        what_happened=event.summary,
        sources=[raw_news.source],
        causal_chain_summary=[step.description for step in chain.logic],
        possible_impacts=possible_impacts,
        risk_factors=risk_factors,
        verification_indicators=verification_indicators,
    )
