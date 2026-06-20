"""Tests for event-family-specific verification suggestions."""

from __future__ import annotations

from eventalpha.history import (
    HistoricalAnalogyRetriever,
    build_demo_current_ai_export_context,
    build_seed_historical_cases,
)


def test_ai_export_control_suggestions_do_not_include_rate_policy_terms() -> None:
    """AI export-control analogies should not receive central-bank style suggestions."""
    retriever = HistoricalAnalogyRetriever(build_seed_historical_cases())
    analogy = retriever.retrieve(**build_demo_current_ai_export_context(), limit=1)[0]
    suggestion_text = " ".join(analogy.verification_suggestions).casefold()

    assert "central-bank" not in suggestion_text
    assert "yield curve" not in suggestion_text
    assert "fx" not in suggestion_text
    assert "gpu" in suggestion_text
    assert "export-control" in suggestion_text


def test_rate_policy_suggestions_include_yield_fx_and_central_bank() -> None:
    """Rate-policy analogies should receive macro/rates verification suggestions."""
    retriever = HistoricalAnalogyRetriever(build_seed_historical_cases())
    analogy = retriever.retrieve(
        query="central bank rate cut",
        event_type="rate_policy",
        limit=1,
    )[0]
    suggestion_text = " ".join(analogy.verification_suggestions).casefold()

    assert "central-bank" in suggestion_text
    assert "yield curve" in suggestion_text
    assert "fx" in suggestion_text


def test_geopolitical_oil_suggestions_include_oil_shipping_terms() -> None:
    """Geopolitical oil/shipping analogies should receive supply-chain verification suggestions."""
    retriever = HistoricalAnalogyRetriever(build_seed_historical_cases())
    analogy = retriever.retrieve(
        query="Middle East oil shipping",
        event_type="geopolitical_conflict",
        assets=["crude oil"],
        tags=["shipping"],
        limit=1,
    )[0]
    suggestion_text = " ".join(analogy.verification_suggestions).casefold()

    assert "oil inventories" in suggestion_text
    assert "shipping" in suggestion_text
    assert "production" in suggestion_text
    assert "risk premium" in suggestion_text
