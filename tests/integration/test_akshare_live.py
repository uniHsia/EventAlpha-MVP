"""Optional live AkShare integration test."""

from __future__ import annotations

import os

import pytest

from eventalpha.data_sources import AkShareMarketDataProvider


@pytest.mark.skipif(
    os.getenv("EVENTALPHA_RUN_LIVE_AKSHARE") != "1",
    reason="Set EVENTALPHA_RUN_LIVE_AKSHARE=1 to run live AkShare tests.",
)
def test_live_akshare_hs300_price_series() -> None:
    """Fetch a small live HS300 sample when explicitly enabled."""
    provider = AkShareMarketDataProvider(refresh_cache=True)

    series = provider.get_price_series("沪深300", "2024-01-02", "2024-01-15")

    assert series.points
