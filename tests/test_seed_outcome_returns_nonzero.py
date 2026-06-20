"""Tests for non-zero manual seed outcome returns."""

from __future__ import annotations

from eventalpha.history import build_seed_historical_cases


def test_seed_outcome_returns_are_nonzero_manual_demo_values() -> None:
    """Seed outcomes should carry illustrative, non-zero T+ window returns."""
    for historical_case in build_seed_historical_cases():
        assert historical_case.outcome is not None
        assert historical_case.outcome.outcome_quality == "manual_seed_demo"

        for window in ["T+1", "T+3", "T+7"]:
            values = [
                returns[window]
                for returns in historical_case.outcome.asset_returns.values()
                if window in returns
            ]
            assert values, f"{historical_case.title} missing {window} returns"
            assert any(value != 0.0 for value in values), (
                f"{historical_case.title} has only zero {window} returns"
            )


def test_seed_source_notes_warn_returns_are_not_verified() -> None:
    """Manual seed return notes should not imply real backtest evidence."""
    for historical_case in build_seed_historical_cases():
        source_notes = " ".join(historical_case.source_notes)
        assert "manual seed demo" in source_notes
        assert "not verified historical returns or backtests" in source_notes
