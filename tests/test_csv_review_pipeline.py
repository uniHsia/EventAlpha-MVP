"""CSV provider review pipeline tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from eventalpha.data_sources import CSVMarketDataProvider
from eventalpha.orchestration import run_event_pipeline, run_review_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def test_csv_provider_runs_multi_asset_review(tmp_path) -> None:
    """The review pipeline should work with CSVMarketDataProvider."""
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    csv_path = Path(__file__).parent / "fixtures" / "market_prices_demo.csv"
    raw_news = RawNews(
        **json.loads(fixture.read_text(encoding="utf-8"))[0],
        publish_time=datetime(2026, 6, 18, tzinfo=timezone.utc),
    )
    ledger = LedgerService(tmp_path / "csv_review.sqlite3")
    event_result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = event_result["prediction_ledger_entry"]
    provider = CSVMarketDataProvider(csv_path)

    result = run_review_pipeline(
        prediction=prediction,
        ledger_service=ledger,
        market_data=provider,
        horizon="T+3",
    )

    expected_assets = [
        asset for asset in prediction.predicted_assets if asset.time_window == "T+3"
    ]
    assert len(result["review_results"]) == len(expected_assets)
    assert result["review_summary"].reviewed_assets == len(expected_assets)
    assert result["review_summary"].average_excess_return != 0
