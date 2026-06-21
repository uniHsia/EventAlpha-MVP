"""Tests for EventCard history validation integration."""

from __future__ import annotations

from eventalpha.agents.card_generation import generate_event_card
from eventalpha.history import DEMO_HISTORY_RISK_NOTE, HistoryValidationSummary
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


def test_event_card_merges_history_validation_summary_without_confidence_change() -> None:
    """History summary should enrich card text while preserving impact confidence math."""
    raw_news, event, verification, score, chain, anti_spurious, mapping = _card_inputs()
    baseline = generate_event_card(
        raw_news=raw_news,
        event=event,
        verification=verification,
        score=score,
        chain=chain,
        anti_spurious=anti_spurious,
        mapping=mapping,
    )
    summary = HistoryValidationSummary(
        overall_validation="demo_only",
        confidence_adjustment_hint=0.02,
        top_signals=[
            "priced_in_risk: moderate signal from AI export controls (reliability=demo_only)",
            "second_order_warning: moderate signal from AI export controls (reliability=demo_only)",
        ],
        asset_notes=["semiconductor equipment: second_order_watch (score=0.45, reliability=demo_only)"],
        required_verifications=["Verify GPU orders.", "Validate semiconductor equipment orders."],
        risk_notes=[DEMO_HISTORY_RISK_NOTE],
        reliability="demo_only",
    )

    enhanced = generate_event_card(
        raw_news=raw_news,
        event=event,
        verification=verification,
        score=score,
        chain=chain,
        anti_spurious=anti_spurious,
        mapping=mapping,
        history_validation_summary=summary,
    )

    assert enhanced.history_validation_summary is not None
    assert enhanced.history_validation_summary["overall_validation"] == "demo_only"
    assert any("demo signals" in item for item in enhanced.risk_factors)
    assert any("priced_in_risk" in item for item in enhanced.risk_factors)
    assert any("orders" in item for item in enhanced.verification_indicators)
    assert len(enhanced.risk_factors) <= 6
    assert len(enhanced.verification_indicators) <= 8
    assert enhanced.possible_impacts == baseline.possible_impacts
    assert enhanced.one_sentence == baseline.one_sentence


def _card_inputs():
    raw_news = RawNews(raw_text="Event text", source="Reuters", source_type="mainstream_media")
    event = StructuredEvent(
        event_id="EVT_CARD_HIST",
        event_title="US expands AI chip export controls",
        summary="Export controls affect AI chips and semiconductor equipment.",
        affected_industries=["semiconductor", "AI infrastructure"],
    )
    verification = EventVerification(
        event_id=event.event_id,
        credibility_score=0.72,
        verification_status="high_confidence",
        risk_flags=["Policy details are incomplete."],
    )
    score = ImpactScore(event_id=event.event_id, event_level="A", impact_score=80)
    chain = CausalChain(
        event_id=event.event_id,
        logic=[
            CausalStep(order=1, description="Export controls restrict GPU supply."),
            CausalStep(order=2, description="Second-order equipment mapping needs verification."),
        ],
        confidence=0.7,
    )
    anti_spurious = AntiSpuriousCheck(
        event_id=event.event_id,
        chain_id=chain.chain_id,
        issues=["Second-order watch assets need extra verification."],
        required_verifications=["Check official policy details."],
        adjusted_confidence=0.6,
    )
    mapping = MarketMapping(
        event_id=event.event_id,
        mapped_assets=[
            MappedAsset(
                asset_name="AI chips",
                relation="direct_beneficiary",
                direction="up",
                confidence=0.8,
            ),
        ],
        watch_indicators=["Track GPU order data."],
    )
    return raw_news, event, verification, score, chain, anti_spurious, mapping
