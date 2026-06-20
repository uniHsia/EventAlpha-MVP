"""Tests for historical analogy explanations."""

from __future__ import annotations

from eventalpha.history import (
    HistoricalAnalogyExplainer,
    retrieve_analogies_for_query,
    build_seed_historical_cases,
)
from eventalpha.schemas import RISK_DISCLAIMER


def test_explainer_includes_required_sections() -> None:
    """Explanation should include similarities, differences, lessons, and risks."""
    analogy = retrieve_analogies_for_query(
        "AI chip export control",
        build_seed_historical_cases(),
        limit=1,
    )[0]

    text = HistoricalAnalogyExplainer().explain_many([analogy])

    assert "similarities=" in text
    assert "differences=" in text
    assert "transferable_lessons=" in text
    assert "non_transferable_lessons=" in text
    assert "verification_suggestions=" in text
    assert "risk_notes=" in text
    assert RISK_DISCLAIMER in text
