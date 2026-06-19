"""ProviderRouter CSV review tests."""

from __future__ import annotations

from pathlib import Path

from eventalpha.data_sources import ProviderRouter


def test_router_calculates_csv_asset_and_benchmark_returns() -> None:
    """CSV proxy assets should calculate returns through the router."""
    csv_path = Path(__file__).parent / "fixtures" / "market_prices_demo.csv"
    router = ProviderRouter(
        csv_path=csv_path,
        default_event_type="ai_export_control",
    )

    asset_return = router.get_asset_return(
        "国产 AI 芯片",
        "T+3",
        start_date="2026-06-18",
    )
    benchmark_return = router.get_benchmark_return(
        "沪深300",
        "T+3",
        start_date="2026-06-18",
    )

    assert asset_return > 0
    assert benchmark_return > 0
    assert asset_return > benchmark_return
