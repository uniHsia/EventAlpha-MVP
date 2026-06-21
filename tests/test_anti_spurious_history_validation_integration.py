"""Tests for AntiSpurious history validation integration."""

from __future__ import annotations

from eventalpha.agents.anti_spurious import check_spurious_reasoning
from eventalpha.history import HistoryValidationSummary
from eventalpha.schemas import CausalChain, CausalStep, StructuredEvent


def test_no_history_summary_preserves_rule_based_output() -> None:
    """Without a summary the existing deterministic output should stay unchanged."""
    event, chain = _inputs()

    baseline = check_spurious_reasoning(event, chain)
    explicit_none = check_spurious_reasoning(event, chain, history_validation_summary=None)

    assert explicit_none.spurious_risk == baseline.spurious_risk
    assert explicit_none.issues == baseline.issues
    assert explicit_none.required_verifications == baseline.required_verifications
    assert explicit_none.adjusted_confidence == baseline.adjusted_confidence


def test_second_order_and_priced_in_signals_add_issues() -> None:
    """History warnings should surface as anti-spurious issues."""
    event, chain = _inputs()
    summary = HistoryValidationSummary(
        overall_validation="demo_only",
        top_signals=[
            "second_order_warning: moderate signal from historical case (reliability=demo_only)",
            "priced_in_risk: moderate signal from historical case (reliability=demo_only)",
        ],
        reliability="demo_only",
    )

    check = check_spurious_reasoning(event, chain, history_validation_summary=summary)

    assert any("second-order" in issue for issue in check.issues)
    assert any("priced in" in issue for issue in check.issues)


def test_requires_verification_adds_required_verifications() -> None:
    """Verification-heavy history should flow into required verifications."""
    event, chain = _inputs()
    summary = HistoryValidationSummary(
        overall_validation="demo_only",
        top_signals=["requires_verification: strong signal from historical case (reliability=demo_only)"],
        required_verifications=["Verify GPU orders and policy implementation."],
        reliability="demo_only",
    )

    check = check_spurious_reasoning(event, chain, history_validation_summary=summary)

    assert any("GPU orders" in item for item in check.required_verifications)


def test_historically_weakened_raises_risk_conservatively_for_demo_only() -> None:
    """Demo-only weakening should not raise low risk beyond medium."""
    event, chain = _inputs()
    summary = HistoryValidationSummary(
        overall_validation="historically_weakened",
        top_signals=["weakens_chain: strong signal from historical case (reliability=demo_only)"],
        reliability="demo_only",
    )

    check = check_spurious_reasoning(event, chain, history_validation_summary=summary)

    assert check.spurious_risk == "medium"
    assert check.adjusted_confidence == 0.58
    assert any("weakened" in issue for issue in check.issues)


def test_historically_weakened_non_demo_can_raise_medium_to_high() -> None:
    """Non-demo weakening can raise an already medium rule-based risk to high."""
    event, chain = _inputs(long_chain=True)
    summary = HistoryValidationSummary(
        overall_validation="historically_weakened",
        top_signals=["weakens_chain: strong signal from historical case (reliability=review_backed)"],
        reliability="review_backed",
    )

    check = check_spurious_reasoning(event, chain, history_validation_summary=summary)

    assert check.spurious_risk == "high"
    assert check.adjusted_confidence == 0.45


def _inputs(long_chain: bool = False):
    event = StructuredEvent(
        event_id="EVT_SPUR_HIST",
        event_title="US expands AI chip export controls",
        summary="Export controls affect AI chips.",
        event_type="ai_export_control",
    )
    steps = [
        CausalStep(order=1, description="Policy changes GPU availability."),
        CausalStep(order=2, description="Market attention changes."),
    ]
    if long_chain:
        steps.extend(
            [
                CausalStep(order=3, description="Supplier expectations change."),
                CausalStep(order=4, description="Capital expenditure plans change."),
                CausalStep(order=5, description="Asset pricing changes."),
            ]
        )
    chain = CausalChain(
        event_id=event.event_id,
        logic=steps,
        affected_assets=["AI chips"],
        confidence=0.7,
    )
    return event, chain
