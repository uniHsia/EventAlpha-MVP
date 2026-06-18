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


def _impact_text(asset_name: str, direction: str, final_confidence: float) -> str:
    confidence_text = f"final_confidence={final_confidence:.2f}"
    if direction == "up":
        return f"{asset_name}: 可能受益或受到市场关注（{confidence_text}）"
    if direction == "down":
        return f"{asset_name}: 可能承压（{confidence_text}）"
    return f"{asset_name}: 需要继续观察（{confidence_text}）"


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
    risk_factors = list(verification.risk_flags) + list(anti_spurious.issues)
    if not risk_factors:
        risk_factors = ["市场可能已经提前反映相关信息"]

    return EventCard(
        event_id=event.event_id,
        event_title=event.event_title,
        event_level=score.event_level,
        credibility_score=verification.credibility_score,
        one_sentence=(
            f"{event.event_title}可能影响{', '.join(event.affected_industries[:3]) or '相关市场'}，"
            "需要结合后续市场数据验证。"
        ),
        what_happened=event.summary,
        sources=[raw_news.source],
        causal_chain_summary=[step.description for step in chain.logic],
        possible_impacts=possible_impacts,
        risk_factors=risk_factors,
        verification_indicators=mapping.watch_indicators
        + anti_spurious.required_verifications,
    )
