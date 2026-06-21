"""Tests for the case-based causal validator."""

from __future__ import annotations

from eventalpha.history import (
    CaseBasedCausalValidator,
    HistoricalAnalogy,
    HistoricalOutcomeComparison,
    OutcomeWindowComparison,
)
from eventalpha.schemas import CausalChain, CausalStep, MappedAsset, MarketMapping, StructuredEvent


def test_no_analogies_returns_insufficient_history() -> None:
    """Without analogies, validation should be explicitly insufficient."""
    event, chain, mapping = _current_inputs()

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [], [])

    assert validation.overall_validation == "insufficient_history"
    assert validation.confidence_adjustment_hint == 0.0
    assert validation.signals[0].signal_type == "insufficient_evidence"


def test_strong_analogy_comparable_supports_chain_without_mutating_confidence() -> None:
    """Strong comparable history should support the chain and leave confidence unchanged."""
    event, chain, mapping = _current_inputs()
    original_confidence = chain.confidence
    analogy = _analogy(strength_label="strong")
    comparison = _comparison(status="comparable", reliability="review_backed", matches=[True, True, True])

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [analogy], [comparison])

    assert any(signal.signal_type == "supports_chain" for signal in validation.signals)
    assert validation.overall_validation == "historically_supported"
    assert validation.confidence_adjustment_hint == 0.05
    assert chain.confidence == original_confidence


def test_mixed_outcome_requires_verification() -> None:
    """Mixed outcome comparison should request verification."""
    event, chain, mapping = _current_inputs()
    analogy = _analogy()
    comparison = _comparison(status="mixed_or_inconclusive", reliability="preliminary", matches=[True, False, None])

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [analogy], [comparison])

    assert any(signal.signal_type == "requires_verification" for signal in validation.signals)
    assert validation.overall_validation == "mixed_or_inconclusive"


def test_demo_only_reliability_adds_risk_note() -> None:
    """Demo-only signals must be clearly marked as illustrative."""
    event, chain, mapping = _current_inputs()
    analogy = _analogy()
    comparison = _comparison(status="comparable", reliability="demo_only", matches=[True, True, True])

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [analogy], [comparison])

    assert validation.overall_validation == "demo_only"
    assert any("illustrative only" in note for note in validation.risk_notes)
    assert all(signal.reliability == "demo_only" for signal in validation.signals)


def test_second_order_lesson_generates_warning() -> None:
    """Second-order historical lessons should generate a warning when current chain matches."""
    event, chain, mapping = _current_inputs()
    analogy = _analogy(
        lessons=[
            "Separate direct chip restrictions from second-order equipment or EDA mapping.",
            "Validate capex with orders and backlog.",
        ]
    )
    comparison = _comparison(status="comparable", reliability="demo_only", matches=[True, True, True])

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [analogy], [comparison])

    assert any(signal.signal_type == "second_order_warning" for signal in validation.signals)


def test_priced_in_lesson_generates_priced_in_risk() -> None:
    """Priced-in lessons should generate pricing risk signals."""
    event, chain, mapping = _current_inputs()
    analogy = _analogy(lessons=["Check whether market pricing already reflected policy rumors."])
    comparison = _comparison(status="comparable", reliability="demo_only", matches=[True, True, True])

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [analogy], [comparison])

    assert any(signal.signal_type == "priced_in_risk" for signal in validation.signals)


def test_second_order_watch_asset_gets_asset_signal() -> None:
    """Market-mapping second_order_watch assets should remain watch signals."""
    event, chain, mapping = _current_inputs()
    analogy = _analogy(lessons=["Second-order equipment and EDA mapping requires verification."])
    comparison = _comparison(status="comparable", reliability="demo_only", matches=[True, True, True])

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [analogy], [comparison])

    equipment = next(signal for signal in validation.asset_signals if signal.asset_name == "semiconductor equipment")
    assert equipment.historical_support == "second_order_watch"
    assert equipment.support_score > 0


def test_asset_reliability_uses_only_contributing_comparisons() -> None:
    """Unmatched historical comparisons should not upgrade asset-level reliability."""
    event, chain, mapping = _current_inputs()
    unrelated = _analogy()
    unrelated.historical_case_id = "HCASE_UNRELATED"
    unrelated.historical_case_title = "Unrelated shipping disruption"
    unrelated.similarities = ["shipping rates and importers"]
    unrelated.transferable_lessons = ["Shipping disruptions need freight-rate verification."]
    unrelated.dimension_scores = []
    comparison = _comparison(status="comparable", reliability="market_backed", matches=[True, True, True])
    comparison.historical_case_id = "HCASE_UNRELATED"

    validation = CaseBasedCausalValidator().validate(event, chain, mapping, [unrelated], [comparison])

    ai_chips = next(signal for signal in validation.asset_signals if signal.asset_name == "AI chips")
    assert ai_chips.historical_support == "insufficient"
    assert ai_chips.reliability == "insufficient"


def _current_inputs():
    event = StructuredEvent(
        event_id="EVT_1",
        event_type="ai_export_control",
        event_title="US expands AI chip export controls",
        summary="Export controls affect GPU supply and domestic substitutes.",
        entities=["US", "China", "GPU"],
        affected_industries=["semiconductor", "AI infrastructure"],
        affected_assets_hint=["AI chips", "semiconductor equipment", "domestic semiconductor substitutes"],
    )
    chain = CausalChain(
        event_id=event.event_id,
        logic=[
            CausalStep(order=1, description="Export controls restrict advanced GPU supply", variable_type="policy"),
            CausalStep(order=2, description="Domestic AI chip substitutes receive attention", variable_type="industry"),
            CausalStep(order=3, description="Second-order equipment and EDA mapping requires verification", variable_type="market"),
        ],
        affected_assets=["AI chips", "semiconductor equipment", "domestic semiconductor substitutes"],
        direction="up",
        confidence=0.78,
    )
    mapping = MarketMapping(
        event_id=event.event_id,
        mapped_assets=[
            MappedAsset(asset_name="AI chips", direction="up", relation="direct_beneficiary"),
            MappedAsset(
                asset_name="semiconductor equipment",
                direction="mixed",
                relation="second_order_watch",
                rationale="Equipment is a second-order mapping requiring orders verification.",
            ),
        ],
    )
    return event, chain, mapping


def _analogy(strength_label: str = "strong", lessons: list[str] | None = None) -> HistoricalAnalogy:
    return HistoricalAnalogy(
        current_event_title="US expands AI chip export controls",
        historical_case_id="HCASE_AI",
        historical_case_title="US advanced chip export controls reshape AI hardware supply chains",
        overall_score=0.75 if strength_label == "strong" else 0.45,
        strength_label=strength_label,
        similarities=["affected_assets overlap: AI chips, semiconductor equipment"],
        transferable_lessons=lessons or ["Separate direct chip restrictions from second-order equipment or EDA mapping."],
        non_transferable_lessons=["Seed outcome is illustrative demo data, not verified backtest evidence."],
        verification_suggestions=["Verify GPU orders and semiconductor supply-chain exposure."],
    )


def _comparison(
    status: str,
    reliability: str,
    matches: list[bool | None],
) -> HistoricalOutcomeComparison:
    return HistoricalOutcomeComparison(
        historical_case_id="HCASE_AI",
        historical_case_title="US advanced chip export controls reshape AI hardware supply chains",
        analogy_score=0.75,
        analogy_strength_label="strong",
        comparison_status=status,
        comparison_reliability=reliability,
        window_comparisons=[
            OutcomeWindowComparison(window=f"T+{index}", direction_match=match)
            for index, match in enumerate(matches, start=1)
        ],
        matched_lessons=["Separate direct chip restrictions from second-order equipment or EDA mapping."],
    )
