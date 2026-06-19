"""AkShare cache tests without live network."""

from __future__ import annotations

import pandas as pd

from eventalpha.data_sources import AkShareMarketDataProvider


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "日期": [
                "2026-06-18",
                "2026-06-19",
                "2026-06-22",
                "2026-06-23",
            ],
            "收盘": [100, 101, 102, 103],
        }
    )


def test_akshare_cache_write_and_read(tmp_path, monkeypatch) -> None:
    """Provider should write cache and reuse it without a second fetch."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)
    calls = {"count": 0}

    def fake_fetch(secid, start_date, end_date, asset_name):
        calls["count"] += 1
        return _df()

    monkeypatch.setattr(provider, "_fetch_eastmoney_direct_dataframe", fake_fetch)

    first = provider.get_price_series("沪深300", "2026-06-18", "2026-06-25")
    second = provider.get_price_series("沪深300", "2026-06-18", "2026-06-25")

    assert calls["count"] == 1
    assert first.points == second.points
    assert list(tmp_path.glob("*.csv"))


def test_refresh_cache_forces_fetch(tmp_path, monkeypatch) -> None:
    """refresh_cache=True should ignore an existing cache file."""
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)
    calls = {"count": 0}

    def fake_fetch(secid, start_date, end_date, asset_name):
        calls["count"] += 1
        return _df()

    monkeypatch.setattr(provider, "_fetch_eastmoney_direct_dataframe", fake_fetch)
    provider.get_price_series("沪深300", "2026-06-18", "2026-06-25")

    refresh_provider = AkShareMarketDataProvider(cache_dir=tmp_path, refresh_cache=True)
    monkeypatch.setattr(refresh_provider, "_fetch_eastmoney_direct_dataframe", fake_fetch)
    refresh_provider.get_price_series("沪深300", "2026-06-18", "2026-06-25")

    assert calls["count"] == 2
