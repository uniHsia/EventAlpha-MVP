"""Mock review pipeline."""

from __future__ import annotations

from typing import Any

from eventalpha.agents import review_prediction, summarize_reviews
from eventalpha.data_sources import MockMarketDataProvider, MarketDataProvider
from eventalpha.schemas import PredictionLedgerEntry
from eventalpha.services import LedgerService, update_rule_from_review


def run_review_pipeline(
    prediction: PredictionLedgerEntry | None = None,
    prediction_id: str | None = None,
    ledger_service: LedgerService | None = None,
    market_data: MarketDataProvider | None = None,
    horizon: str = "T+3",
    persist: bool = True,
) -> dict[str, Any]:
    """Run mock review and rule update for one prediction."""
    ledger = ledger_service or LedgerService()
    provider = market_data or MockMarketDataProvider()

    if prediction is None and prediction_id:
        prediction = ledger.get_prediction(prediction_id)
    if prediction is None:
        prediction = ledger.get_latest_prediction()
    if prediction is None:
        raise ValueError("No prediction ledger entry found for review.")

    review_results = review_prediction(prediction, provider, horizon=horizon)
    review_summary = summarize_reviews(prediction, review_results, horizon=horizon)
    rule_update = update_rule_from_review(prediction, review_summary)

    if persist:
        for review_result in review_results:
            ledger.save_review_result(review_result)
        ledger.save_review_summary(review_summary)
        ledger.save_rule_update(rule_update)

    return {
        "prediction": prediction,
        "review_result": review_results[0] if review_results else None,
        "review_results": review_results,
        "review_summary": review_summary,
        "rule_update": rule_update,
    }
