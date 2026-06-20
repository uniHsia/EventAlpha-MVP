"""Tests for the historical case demo helper."""

from __future__ import annotations

from eventalpha.schemas import RISK_DISCLAIMER
from scripts.run_historical_case_demo import run_historical_case_demo


def test_historical_case_demo_runs_offline() -> None:
    """Default demo should use in-memory seed cases without network."""
    result = run_historical_case_demo(limit=3)

    assert result["used_seed_memory"] is True
    assert len(result["matches"]) == 3
    assert RISK_DISCLAIMER in result["report"]


def test_historical_case_demo_seed_writes_temp_store(tmp_path) -> None:
    """Seed mode should write cases to the selected store path."""
    path = tmp_path / "historical_cases.json"

    result = run_historical_case_demo(seed=True, store_path=path, limit=2)

    assert path.exists()
    assert result["used_seed_memory"] is False
    assert len(result["cases"]) >= 8


def test_historical_case_demo_query_event_type_asset_search(tmp_path) -> None:
    """Demo helper should support query, event_type, and asset search."""
    path = tmp_path / "historical_cases.json"
    run_historical_case_demo(seed=True, store_path=path)

    query_result = run_historical_case_demo(query="AI chip export control", store_path=path)
    type_result = run_historical_case_demo(event_type="rate_policy", store_path=path)
    asset_result = run_historical_case_demo(assets=["crude oil"], store_path=path)

    assert query_result["matches"][0].event_type == "ai_export_control"
    assert type_result["matches"][0].event_type == "rate_policy"
    assert asset_result["matches"]
