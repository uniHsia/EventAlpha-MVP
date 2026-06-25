"""Single-event analysis pipeline."""

from __future__ import annotations

import inspect
from typing import Any

from eventalpha.agents import (
    generate_causal_chain,
    generate_event_card,
    map_event_to_markets,
    RuleBasedAntiSpuriousAgent,
    RuleBasedCausalReasoningAgent,
    RuleBasedExtractionAgent,
    score_event,
    verify_event,
)
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService, build_prediction_entry


def should_write_prediction_ledger(
    event_card,
    market_mapping,
    verification,
    raw_news: RawNews,
    prediction_entry=None,
) -> tuple[bool, str, str]:
    """Return whether this event should enter Prediction Ledger/ReviewTask."""
    cluster_type = raw_news.metadata.get("cluster_type")
    if cluster_type in {"same_source_topic_cluster", "analysis_digest"}:
        return False, "skipped_observation_cluster_type", "观察卡片，未进入预测账本"
    if event_card.event_level not in {"S", "A", "B"}:
        return False, "skipped_low_event_level", "观察卡片，未进入预测账本"
    if (
        float(verification.credibility_score or 0) < 0.50
        or verification.verification_status in {"single_source_low_confidence", "low_confidence", "analysis_only", "conflict_detected"}
    ):
        return False, "skipped_low_confidence", "观察卡片，未进入预测账本"
    has_card_impacts = bool(event_card.possible_impacts)
    has_predicted_assets = bool(getattr(prediction_entry, "predicted_assets", None))
    has_mapping_assets = bool(getattr(market_mapping, "mapped_assets", None))
    if not (has_card_impacts or has_predicted_assets or has_mapping_assets):
        return False, "skipped_no_assets", "观察卡片，未进入预测账本"
    return True, "written", "written"


def run_event_pipeline(
    raw_news: RawNews,
    ledger_service: LedgerService | None = None,
    persist: bool = True,
    extraction_agent=None,
    causal_agent=None,
    anti_spurious_agent=None,
    history_validation_summary=None,
) -> dict[str, Any]:
    """Run the MVP event-analysis pipeline for one raw news item."""
    ledger = ledger_service

    extractor = extraction_agent or RuleBasedExtractionAgent()
    event = extractor.extract(raw_news)
    extraction_warnings = list(getattr(extractor, "warnings", []))
    verification = verify_event(raw_news, event)
    score = score_event(event, verification)
    causal_reasoner = causal_agent or RuleBasedCausalReasoningAgent()
    causal_chain = causal_reasoner.build_chain(
        structured_event=event,
        verification=verification,
        impact_score=score,
        supported_assets=event.affected_assets_hint,
        extraction_warnings=extraction_warnings,
    )
    causal_warnings = list(getattr(causal_reasoner, "warnings", []))
    market_mapping = map_event_to_markets(event, causal_chain)
    anti_spurious_checker = anti_spurious_agent or RuleBasedAntiSpuriousAgent()
    anti_spurious_kwargs = {
        "structured_event": event,
        "causal_chain": causal_chain,
        "verification": verification,
        "impact_score": score,
        "market_mapping": market_mapping,
        "extraction_warnings": extraction_warnings,
        "causal_warnings": causal_warnings,
        "supported_assets": event.affected_assets_hint,
    }
    if _accepts_keyword(anti_spurious_checker.check, "history_validation_summary"):
        anti_spurious_kwargs["history_validation_summary"] = history_validation_summary
    anti_spurious = anti_spurious_checker.check(**anti_spurious_kwargs)
    anti_spurious_warnings = list(getattr(anti_spurious_checker, "warnings", []))
    event_card = generate_event_card(
        raw_news,
        event,
        verification,
        score,
        causal_chain,
        anti_spurious,
        market_mapping,
        history_validation_summary=history_validation_summary,
    )
    prediction = build_prediction_entry(
        event,
        verification,
        score,
        causal_chain,
        anti_spurious,
        market_mapping,
    )
    gate_allowed, gate_status, gate_reason = should_write_prediction_ledger(
        event_card=event_card,
        market_mapping=market_mapping,
        verification=verification,
        raw_news=raw_news,
        prediction_entry=prediction,
    )
    event_card = event_card.model_copy(
        update={
            "prediction_gate_status": gate_status,
            "prediction_gate_reason": gate_reason if gate_status != "written" else None,
        }
    )

    review_tasks = []
    if persist:
        ledger = ledger or LedgerService()
        ledger.save_raw_news(raw_news)
        ledger.save_event(event)
        ledger.save_verification(verification)
        ledger.save_score(score)
        ledger.save_causal_chain(causal_chain)
        ledger.save_anti_spurious_check(anti_spurious)
        ledger.save_market_mapping(market_mapping)
        ledger.save_event_card(event_card)
        if gate_allowed:
            ledger.save_prediction_ledger(prediction)
            review_tasks = ledger.create_review_tasks(prediction)

    return {
        "raw_news": raw_news,
        "structured_event": event,
        "extraction_warnings": extraction_warnings,
        "verification": verification,
        "impact_score": score,
        "causal_chain": causal_chain,
        "causal_warnings": causal_warnings,
        "anti_spurious_check": anti_spurious,
        "anti_spurious_warnings": anti_spurious_warnings,
        "market_mapping": market_mapping,
        "event_card": event_card,
        "history_validation_summary": history_validation_summary,
        "prediction_ledger_entry": prediction,
        "review_tasks": review_tasks,
        "prediction_gate": {
            "allowed": gate_allowed,
            "status": gate_status,
            "reason": gate_reason,
        },
    }


def _accepts_keyword(callable_obj, keyword: str) -> bool:
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return False
    return keyword in signature.parameters
