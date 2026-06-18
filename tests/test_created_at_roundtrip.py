"""Created-at persistence tests for ledger objects."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline, run_review_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def _load_raw_news(index: int = 0) -> RawNews:
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    return RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[index])


def test_prediction_and_asset_created_at_roundtrip(tmp_path) -> None:
    """Prediction and predicted asset timestamps should survive DB reads."""
    ledger = LedgerService(tmp_path / "created_at.sqlite3")
    result = run_event_pipeline(_load_raw_news(), ledger_service=ledger)
    prediction = result["prediction_ledger_entry"]

    loaded = ledger.get_prediction(prediction.prediction_id)

    assert loaded is not None
    assert loaded.created_at == prediction.created_at
    assert [asset.created_at for asset in loaded.predicted_assets] == [
        asset.created_at for asset in prediction.predicted_assets
    ]


def test_review_and_rule_created_at_are_persisted(tmp_path) -> None:
    """Review result and rule update rows should keep the model created_at."""
    ledger = LedgerService(tmp_path / "review_created_at.sqlite3")
    event_result = run_event_pipeline(_load_raw_news(), ledger_service=ledger)
    prediction = event_result["prediction_ledger_entry"]
    review_result = run_review_pipeline(prediction=prediction, ledger_service=ledger)

    review = review_result["review_results"][0]
    update = review_result["rule_update"]
    review_rows = ledger.get_review_results(prediction.prediction_id)
    update_rows = ledger.get_rule_updates(prediction.prediction_id)

    assert review_rows[0]["created_at"] == review.created_at.isoformat()
    assert update_rows[0]["created_at"] == update.created_at.isoformat()
