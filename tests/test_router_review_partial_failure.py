"""Router review partial failure behavior tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from eventalpha.agents.review_learning import review_asset, summarize_reviews
from eventalpha.data_sources import ProviderRouter
from eventalpha.schemas import MarketDataError, PredictedAsset, PredictionLedgerEntry


class FailingAkShareProvider:
    """AkShare stand-in that always fails."""

    def get_price_series(self, asset_name: str, start_date: str, end_date: str):
        raise MarketDataError("AkShare unavailable")

    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        raise MarketDataError("AkShare unavailable")

    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        raise MarketDataError("AkShare unavailable")


def test_router_review_can_continue_after_akshare_failure() -> None:
    """A failing AkShare asset should not prevent CSV assets from reviewing."""
    csv_path = Path(__file__).parent / "fixtures" / "market_prices_demo.csv"
    router = ProviderRouter(
        csv_path=csv_path,
        akshare_provider=FailingAkShareProvider(),
        default_event_type="geopolitical_conflict",
    )
    prediction = PredictionLedgerEntry(
        event_id="EVT_ROUTER",
        event_title="Router partial failure",
        event_type="geopolitical_conflict",
        publish_time=datetime(2026, 6, 18, tzinfo=timezone.utc),
        predicted_assets=[
            PredictedAsset(
                asset_name="国产 AI 芯片",
                asset_type="theme",
                direction="up",
                benchmark="沪深300",
            ),
            PredictedAsset(
                asset_name="军工",
                asset_type="index",
                direction="mixed",
                benchmark="沪深300",
            ),
        ],
    )
    reviews = []
    successful_assets = []
    failures = []

    for asset in prediction.predicted_assets:
        try:
            reviews.append(review_asset(prediction, asset, router, horizon="T+3"))
            successful_assets.append(asset)
        except MarketDataError as exc:
            failures.append((asset.asset_name, str(exc)))

    summary = summarize_reviews(
        prediction.model_copy(update={"predicted_assets": successful_assets}),
        reviews,
        horizon="T+3",
    )

    assert [review.asset_name for review in reviews] == ["国产 AI 芯片"]
    assert len(failures) == 1
    assert failures[0][0] == "军工"
    assert "AkShare unavailable" in failures[0][1]
    assert "All provider routes failed" in failures[0][1]
    assert summary.reviewed_assets == 1
