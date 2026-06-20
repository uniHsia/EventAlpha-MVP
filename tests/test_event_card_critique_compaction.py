"""Tests for EventCard risk and verification compaction."""

from __future__ import annotations

from eventalpha.agents.card_generation import generate_event_card
from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    CausalStep,
    EventVerification,
    ImpactScore,
    MappedAsset,
    MarketMapping,
    RawNews,
    StructuredEvent,
)


def test_event_card_compacts_critique_lists() -> None:
    """EventCard should preserve key flags while keeping list sizes bounded."""
    raw_news = RawNews(raw_text="Event text", source="Reuters", source_type="mainstream_media")
    event = StructuredEvent(
        event_id="EVT_CARD",
        event_title="Policy event",
        summary="Summary",
        affected_industries=["Energy", "Shipping", "FX"],
    )
    verification = EventVerification(
        event_id="EVT_CARD",
        credibility_score=0.73,
        verification_status="high_confidence",
        risk_flags=[
            "Policy details are still incomplete.",
            "The market may have partly priced this in already.",
        ],
    )
    score = ImpactScore(event_id="EVT_CARD", event_level="A", impact_score=80)
    chain = CausalChain(
        event_id="EVT_CARD",
        logic=[
            CausalStep(order=1, description="policy"),
            CausalStep(order=2, description="supply"),
            CausalStep(order=3, description="asset"),
        ],
    )
    anti_spurious = AntiSpuriousCheck(
        event_id="EVT_CARD",
        chain_id=chain.chain_id,
        issues=[
            "Insufficient evidence supports a direct jump from the event to the asset.",
            "Unsupported asset mapping reaches too far from the event.",
            "Second-order watch assets need extra verification.",
            "The causal chain is too long for confidence.",
            "The market may already have priced this in.",
            "Need follow-up.",
        ],
        required_verifications=[
            "Check the official filing and regulator notice.",
            "Check order backlog and bidding updates.",
            "Validate the proxy asset mapping against supplier lists.",
            "Track the yield curve and FX response.",
            "Track inventory and shipment data.",
            "Keep following up.",
        ],
        adjusted_confidence=0.6,
    )
    mapping = MarketMapping(
        event_id="EVT_CARD",
        mapped_assets=[
            MappedAsset(asset_name="Energy", relation="direct_beneficiary", direction="up")
        ],
        watch_indicators=[
            "Check order backlog and bidding updates.",
            "Validate the proxy asset mapping against supplier lists.",
            "Track the yield curve and FX response.",
            "Track inventory and shipment data.",
            "Monitor policy implementation details.",
            "Observe cross-asset confirmation.",
        ],
    )

    card = generate_event_card(
        raw_news=raw_news,
        event=event,
        verification=verification,
        score=score,
        chain=chain,
        anti_spurious=anti_spurious,
        mapping=mapping,
    )

    assert len(card.risk_factors) <= 6
    assert len(card.verification_indicators) <= 8
    assert "Policy details are still incomplete." in card.risk_factors
    assert any("Insufficient evidence" in item for item in card.risk_factors)
    assert any("official filing" in item for item in card.verification_indicators)
