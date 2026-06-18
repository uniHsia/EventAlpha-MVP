"""Tests for SQLite ledger persistence."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline, run_review_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def test_ledger_persists_prediction_review_and_rule_update(tmp_path) -> None:
    """Ledger service should persist the minimum event-review loop."""
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    raw_news = RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])
    ledger = LedgerService(tmp_path / "eventalpha_ledger.sqlite3")

    event_result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = event_result["prediction_ledger_entry"]
    loaded = ledger.get_prediction(prediction.prediction_id)

    assert loaded is not None
    assert loaded.prediction_id == prediction.prediction_id
    assert loaded.predicted_assets

    review_result = run_review_pipeline(
        prediction=loaded,
        ledger_service=ledger,
        horizon="T+3",
    )

    review_rows = ledger.get_review_results(prediction.prediction_id)
    update_rows = ledger.get_rule_updates(prediction.prediction_id)

    assert review_rows
    assert update_rows
    assert review_rows[0]["review_id"] == review_result["review_result"].review_id
    assert update_rows[0]["review_id"] == review_result["rule_update"].review_id
