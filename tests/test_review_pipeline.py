"""Tests for the mock review pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eventalpha.orchestration import run_event_pipeline, run_review_pipeline
from eventalpha.schemas import RawNews, ReviewResult
from eventalpha.services import LedgerService


def _seed_prediction(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    raw_news = RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])
    ledger = LedgerService(tmp_path / "eventalpha_review.sqlite3")
    event_result = run_event_pipeline(raw_news, ledger_service=ledger)
    return ledger, event_result["prediction_ledger_entry"]


def test_mock_review_outputs_review_result(tmp_path) -> None:
    """T+3 mock review should compare asset returns against the benchmark."""
    ledger, prediction = _seed_prediction(tmp_path)

    result = run_review_pipeline(
        prediction=prediction,
        ledger_service=ledger,
        horizon="T+3",
    )
    review = result["review_result"]

    assert isinstance(review, ReviewResult)
    assert review.actual_return is not None
    assert review.benchmark_return is not None
    assert review.excess_return == pytest.approx(
        review.actual_return - review.benchmark_return
    )
    assert isinstance(review.direction_correct, bool)
    assert review.causal_validity in {"valid", "partially_valid", "invalid", "unknown"}
    assert review.review_conclusion
    assert result["rule_update"].prediction_id == prediction.prediction_id
