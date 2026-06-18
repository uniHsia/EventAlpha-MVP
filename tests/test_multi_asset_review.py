"""Multi-asset review tests."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline, run_review_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def test_prediction_reviews_all_assets_for_horizon(tmp_path) -> None:
    """All AI prediction assets with T+3 horizon should be reviewed."""
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    raw_news = RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])
    ledger = LedgerService(tmp_path / "multi_asset.sqlite3")
    event_result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = event_result["prediction_ledger_entry"]

    result = run_review_pipeline(prediction=prediction, ledger_service=ledger, horizon="T+3")
    reviews = result["review_results"]
    summary = result["review_summary"]

    expected_count = len(
        [asset for asset in prediction.predicted_assets if asset.time_window == "T+3"]
    )
    assert len(reviews) == expected_count
    assert summary.total_assets == expected_count
    assert summary.reviewed_assets == expected_count
    assert len(ledger.get_review_results(prediction.prediction_id)) == expected_count
