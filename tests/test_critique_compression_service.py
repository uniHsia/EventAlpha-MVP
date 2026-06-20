"""Tests for critique compression service."""

from __future__ import annotations

from eventalpha.services import CritiqueCompressionService


def test_compresses_and_prioritizes_issues() -> None:
    """Issues should be deduplicated by concept and capped at five."""
    service = CritiqueCompressionService()
    result = service.compress_anti_spurious(
        issues=[
            "Insufficient evidence supports a direct jump from the event to the asset.",
            "Need more evidence before making a direct jump to the asset.",
            "The market may already have priced this in.",
            "Unsupported asset mapping reaches too far from the event.",
            "Second-order watch assets need extra verification.",
            "The causal chain is too long for confidence.",
            "Need follow-up.",
        ],
        required_verifications=[
            "Check the official filing.",
        ],
    )

    assert len(result.issues) == 5
    assert any("Insufficient evidence" in item for item in result.issues)
    assert any("priced" in item for item in result.issues)
    assert any("Unsupported asset mapping" in item for item in result.issues)
    assert not any(item == "Need follow-up." for item in result.issues)
    assert result.raw_issue_count == 7


def test_compresses_required_verifications_by_priority() -> None:
    """Required verifications should deduplicate concepts and keep top priorities."""
    service = CritiqueCompressionService()
    result = service.compress_anti_spurious(
        issues=["Need more evidence."],
        required_verifications=[
            "Check the official filing and regulator notice.",
            "Confirm the official notice before reacting.",
            "Check order backlog and bidding updates.",
            "Validate the proxy asset mapping against supplier lists.",
            "Track the yield curve and FX response.",
            "Keep following up.",
        ],
    )

    assert len(result.required_verifications) <= 5
    assert result.required_verifications[0] == "Check the official filing and regulator notice."
    assert any("order backlog" in item for item in result.required_verifications)
    assert any("proxy asset mapping" in item for item in result.required_verifications)
    assert not any(item == "Keep following up." for item in result.required_verifications)
    assert result.raw_required_verification_count == 6
