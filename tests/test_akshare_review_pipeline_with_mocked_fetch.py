"""Review pipeline test with AkShareProvider and mocked fetch."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from eventalpha.data_sources import AkShareMarketDataProvider
from eventalpha.orchestration import run_review_pipeline
from eventalpha.schemas import PredictedAsset, PredictionLedgerEntry


def test_akshare_provider_runs_review_pipeline_with_mocked_fetch(tmp_path, monkeypatch) -> None:
    """AkShareProvider should work as a MarketDataProvider without live network."""
    prediction = PredictionLedgerEntry(
        event_id="EVT_AK",
        event_title="中证军工测试",
        event_type="geopolitical_conflict",
        publish_time=datetime(2026, 6, 18, tzinfo=timezone.utc),
        predicted_assets=[
            PredictedAsset(
                asset_name="中证军工",
                asset_type="index",
                direction="up",
                benchmark="沪深300",
                asset_confidence=0.7,
                chain_confidence=0.7,
                anti_spurious_adjusted_confidence=0.7,
            )
        ],
    )
    provider = AkShareMarketDataProvider(cache_dir=tmp_path)

    def fake_fetch(secid, start_date, end_date, asset_name):
        if asset_name == "中证军工":
            closes = [100, 101, 102, 104, 105, 104, 103, 103]
        else:
            closes = [100, 100.2, 100.4, 100.8, 100.7, 100.6, 100.5, 100.4]
        return pd.DataFrame(
            {
                "日期": [
                    "2026-06-18",
                    "2026-06-19",
                    "2026-06-22",
                    "2026-06-23",
                    "2026-06-24",
                    "2026-06-25",
                    "2026-06-26",
                    "2026-06-29",
                ],
                "收盘": closes,
            }
        )

    monkeypatch.setattr(provider, "_fetch_eastmoney_direct_dataframe", fake_fetch)

    result = run_review_pipeline(
        prediction=prediction,
        market_data=provider,
        horizon="T+3",
        persist=False,
    )

    assert len(result["review_results"]) == 1
    assert result["review_results"][0].asset_name == "中证军工"
    assert result["review_results"][0].actual_return == 0.04
    assert result["review_summary"].reviewed_assets == 1
