"""Tests for the historical analogy demo helper."""

from __future__ import annotations

from scripts.run_historical_analogy_demo import run_historical_analogy_demo


def test_historical_analogy_demo_runs_offline(tmp_path) -> None:
    """Default demo should use in-memory seed cases without network."""
    result = run_historical_analogy_demo(limit=3, store_path=tmp_path / "missing_cases.json")

    assert result["used_seed_memory"] is True
    assert len(result["analogies"]) == 3
    assert "Historical Analogy Matches" in result["report"]


def test_historical_analogy_demo_query_event_type_asset_params() -> None:
    """Demo helper should support query, event_type, and asset parameters."""
    query_result = run_historical_analogy_demo(query="AI chip export control", limit=2)
    type_result = run_historical_analogy_demo(event_type="ai_export_control", limit=1)
    asset_result = run_historical_analogy_demo(assets=["AI chips"], limit=2)

    assert query_result["analogies"][0].historical_case_title.startswith("US advanced chip")
    assert type_result["analogies"][0].historical_case_title.startswith("US advanced chip")
    assert asset_result["analogies"]
