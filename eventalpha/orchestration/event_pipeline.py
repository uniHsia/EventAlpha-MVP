"""Single-event analysis pipeline."""

from __future__ import annotations

from typing import Any

from eventalpha.agents import (
    check_spurious_reasoning,
    extract_event,
    generate_causal_chain,
    generate_event_card,
    map_event_to_markets,
    score_event,
    verify_event,
)
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService, build_prediction_entry


def run_event_pipeline(
    raw_news: RawNews,
    ledger_service: LedgerService | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run the MVP event-analysis pipeline for one raw news item."""
    ledger = ledger_service or LedgerService()

    event = extract_event(raw_news)
    verification = verify_event(raw_news, event)
    score = score_event(event, verification)
    causal_chain = generate_causal_chain(event, score)
    anti_spurious = check_spurious_reasoning(event, causal_chain)
    market_mapping = map_event_to_markets(event, causal_chain)
    event_card = generate_event_card(
        raw_news,
        event,
        verification,
        score,
        causal_chain,
        anti_spurious,
        market_mapping,
    )
    prediction = build_prediction_entry(
        event,
        verification,
        score,
        causal_chain,
        anti_spurious,
        market_mapping,
    )

    review_tasks = []
    if persist:
        ledger.save_raw_news(raw_news)
        ledger.save_event(event)
        ledger.save_verification(verification)
        ledger.save_score(score)
        ledger.save_causal_chain(causal_chain)
        ledger.save_anti_spurious_check(anti_spurious)
        ledger.save_market_mapping(market_mapping)
        ledger.save_event_card(event_card)
        ledger.save_prediction_ledger(prediction)
        review_tasks = ledger.create_review_tasks(prediction)

    return {
        "raw_news": raw_news,
        "structured_event": event,
        "verification": verification,
        "impact_score": score,
        "causal_chain": causal_chain,
        "anti_spurious_check": anti_spurious,
        "market_mapping": market_mapping,
        "event_card": event_card,
        "prediction_ledger_entry": prediction,
        "review_tasks": review_tasks,
    }
