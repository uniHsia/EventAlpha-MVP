"""Rule-based case validation for current causal chains."""

from __future__ import annotations

import re
from typing import Iterable

from eventalpha.schemas import CausalChain, MarketMapping, StructuredEvent

from .analogy import HistoricalAnalogy
from .causal_validation import (
    AssetLevelHistoricalSignal,
    CaseBasedCausalValidation,
    CausalValidationSignal,
)
from .outcome_comparison import HistoricalOutcomeComparison


DEMO_ONLY_RISK_NOTE = (
    "Historical validation uses manual_seed_demo or mock_demo signals; treat this as illustrative only, "
    "not real market evidence."
)
RESEARCH_RISK_NOTE = "Case-based causal validation is a research aid and not investment advice."

PRICED_IN_TERMS = ["priced in", "pricing", "market pricing", "rumor", "already priced"]
SECOND_ORDER_TERMS = [
    "second-order",
    "second order",
    "equipment",
    "eda",
    "capex",
    "orders",
    "backlog",
    "supplier commentary",
    "supplier",
]
VERIFICATION_TERMS = ["verify", "verification", "check", "watch", "validate", "confirm"]
RELIABILITY_RANK = {
    "insufficient": 0,
    "demo_only": 1,
    "preliminary": 2,
    "review_backed": 3,
    "market_backed": 4,
}


class CaseBasedCausalValidator:
    """Validate a current causal chain against historical analogies and outcomes."""

    def validate(
        self,
        structured_event: StructuredEvent,
        causal_chain: CausalChain,
        market_mapping: MarketMapping | None,
        analogies: list[HistoricalAnalogy],
        outcome_comparisons: list[HistoricalOutcomeComparison],
    ) -> CaseBasedCausalValidation:
        """Build a deterministic case-based causal validation result."""
        comparison_by_case = {
            comparison.historical_case_id: comparison
            for comparison in outcome_comparisons
        }
        risk_notes = [RESEARCH_RISK_NOTE]
        validation_notes = [
            "Validator does not mutate the causal chain or ledger confidence.",
            "Historical signals are explanatory metadata for later review layers.",
        ]

        if not analogies:
            return CaseBasedCausalValidation(
                current_event_title=structured_event.event_title,
                event_type=structured_event.event_type,
                overall_validation="insufficient_history",
                confidence_adjustment_hint=0.0,
                signals=[
                    CausalValidationSignal(
                        signal_type="insufficient_evidence",
                        strength="weak",
                        rationale="No historical analogies were available for this event.",
                        reliability="insufficient",
                        risk_notes=[RESEARCH_RISK_NOTE],
                    )
                ],
                required_verifications=["Add or retrieve historical analogies before drawing case-based conclusions."],
                validation_notes=validation_notes,
                risk_notes=risk_notes,
            )

        signals: list[CausalValidationSignal] = []
        transferable_lessons: list[str] = []
        non_transferable_lessons: list[str] = []
        required_verifications: list[str] = []

        context_text = _context_text(structured_event, causal_chain, market_mapping)
        for analogy in analogies:
            comparison = comparison_by_case.get(analogy.historical_case_id)
            reliability = _comparison_reliability(comparison)
            case_risk_notes = _case_risk_notes(reliability)
            if reliability == "demo_only":
                risk_notes.append(DEMO_ONLY_RISK_NOTE)

            transferable_lessons.extend(analogy.transferable_lessons)
            non_transferable_lessons.extend(analogy.non_transferable_lessons)
            required_verifications.extend(analogy.verification_suggestions)
            if comparison:
                required_verifications.extend(comparison.mismatch_reasons)
                required_verifications.extend(comparison.validation_notes)
                risk_notes.extend(comparison.risk_notes)

            case_signal = _case_signal(analogy, comparison, reliability, causal_chain, case_risk_notes)
            if case_signal:
                signals.append(case_signal)

            lesson_text = _joined_text(analogy.transferable_lessons, analogy.non_transferable_lessons)
            if _contains_any(lesson_text, PRICED_IN_TERMS):
                signals.append(
                    _signal(
                        analogy,
                        "priced_in_risk",
                        "moderate",
                        "Historical lessons warn that market pricing or rumors may already reflect the event.",
                        reliability,
                        risk_notes=case_risk_notes,
                    )
                )
            if _contains_any(lesson_text, SECOND_ORDER_TERMS) and _contains_any(context_text, SECOND_ORDER_TERMS):
                signals.append(
                    _signal(
                        analogy,
                        "second_order_warning",
                        "moderate",
                        "Historical lessons caution that second-order mappings require verification.",
                        reliability,
                        affected_chain_steps=_matching_chain_steps(causal_chain, SECOND_ORDER_TERMS),
                        related_assets=_second_order_assets(causal_chain, market_mapping),
                        risk_notes=case_risk_notes,
                    )
                )

        asset_signals = _asset_signals(
            market_mapping=market_mapping,
            causal_chain=causal_chain,
            analogies=analogies,
            comparison_by_case=comparison_by_case,
        )
        overall, hint = _overall_validation(signals)

        if overall == "demo_only":
            risk_notes.append(DEMO_ONLY_RISK_NOTE)

        return CaseBasedCausalValidation(
            current_event_title=structured_event.event_title,
            event_type=structured_event.event_type,
            overall_validation=overall,
            confidence_adjustment_hint=hint,
            signals=_dedupe_signals(signals),
            asset_signals=asset_signals,
            transferable_lessons=_unique(transferable_lessons)[:12],
            non_transferable_lessons=_unique(non_transferable_lessons)[:12],
            required_verifications=_unique(required_verifications)[:15],
            validation_notes=_unique(validation_notes),
            risk_notes=_unique(risk_notes),
        )


def _case_signal(
    analogy: HistoricalAnalogy,
    comparison: HistoricalOutcomeComparison | None,
    reliability: str,
    causal_chain: CausalChain,
    risk_notes: list[str],
) -> CausalValidationSignal | None:
    if comparison is None:
        return _signal(
            analogy,
            "insufficient_evidence",
            "weak",
            "No historical outcome comparison is available for this analogy.",
            reliability,
            risk_notes=risk_notes,
        )

    strength = _signal_strength(analogy)
    if analogy.strength_label in {"strong", "moderate"} and comparison.comparison_status == "comparable":
        return _signal(
            analogy,
            "supports_chain",
            strength,
            "Historical analogy and outcome comparison point in the same direction as the current causal chain.",
            reliability,
            affected_chain_steps=[step.order for step in causal_chain.logic],
            related_assets=list(causal_chain.affected_assets),
            risk_notes=risk_notes,
        )
    if comparison.comparison_status == "mixed_or_inconclusive":
        if _mostly_mismatched(comparison):
            return _signal(
                analogy,
                "weakens_chain",
                strength,
                "Most comparable outcome windows differ from the historical direction.",
                reliability,
                affected_chain_steps=[step.order for step in causal_chain.logic],
                risk_notes=risk_notes,
            )
        return _signal(
            analogy,
            "requires_verification",
            strength,
            "Historical/current outcome windows are mixed or incomplete and require verification.",
            reliability,
            affected_chain_steps=[step.order for step in causal_chain.logic],
            risk_notes=risk_notes,
        )
    if comparison.comparison_status in {"insufficient_current_outcome", "missing_historical_outcome"}:
        return _signal(
            analogy,
            "insufficient_evidence",
            "weak",
            "Historical comparison cannot validate the current chain because outcome evidence is insufficient.",
            reliability,
            risk_notes=risk_notes,
        )
    return None


def _asset_signals(
    *,
    market_mapping: MarketMapping | None,
    causal_chain: CausalChain,
    analogies: list[HistoricalAnalogy],
    comparison_by_case: dict[str, HistoricalOutcomeComparison],
) -> list[AssetLevelHistoricalSignal]:
    assets = list(market_mapping.mapped_assets) if market_mapping else []
    if not assets:
        return [
            AssetLevelHistoricalSignal(
                asset_name=asset,
                historical_support="insufficient",
                support_score=0.0,
                required_verifications=["No market mapping was available for asset-level validation."],
                reliability="insufficient",
            )
            for asset in causal_chain.affected_assets
        ]

    results: list[AssetLevelHistoricalSignal] = []
    for mapped_asset in assets:
        supporting_cases: list[str] = []
        weakening_cases: list[str] = []
        lessons: list[str] = []
        required_verifications: list[str] = []
        reliabilities: list[str] = []
        overlap_hits = 0
        comparable_hits = 0
        mixed_hits = 0

        for analogy in analogies:
            comparison = comparison_by_case.get(analogy.historical_case_id)
            reliability = _comparison_reliability(comparison)
            overlap = _asset_overlap(mapped_asset.asset_name, analogy, causal_chain)
            if overlap:
                if reliability != "insufficient":
                    reliabilities.append(reliability)
                overlap_hits += 1
                lessons.extend(analogy.transferable_lessons[:3])
                required_verifications.extend(analogy.verification_suggestions[:3])
                if comparison and comparison.comparison_status == "comparable":
                    comparable_hits += 1
                    supporting_cases.append(analogy.historical_case_title)
                elif comparison and comparison.comparison_status == "mixed_or_inconclusive":
                    mixed_hits += 1
                    weakening_cases.append(analogy.historical_case_title)
                else:
                    supporting_cases.append(analogy.historical_case_title)

        cautionary = (
            mapped_asset.relation == "second_order_watch"
            or mapped_asset.direction == "mixed"
            or _contains_any(_joined_text([mapped_asset.rationale], lessons), SECOND_ORDER_TERMS + VERIFICATION_TERMS)
        )
        if cautionary:
            support = "second_order_watch"
            score = 0.45 if overlap_hits else 0.25
        elif comparable_hits:
            support = "supported"
            score = min(0.95, 0.55 + 0.15 * comparable_hits + 0.05 * overlap_hits)
        elif mixed_hits or overlap_hits:
            support = "mixed"
            score = 0.45
        else:
            support = "insufficient"
            score = 0.0
            required_verifications.append("Map this asset to historical affected assets before relying on the signal.")

        results.append(
            AssetLevelHistoricalSignal(
                asset_name=mapped_asset.asset_name,
                historical_support=support,
                support_score=score,
                supporting_cases=_unique(supporting_cases)[:5],
                weakening_cases=_unique(weakening_cases)[:5],
                lessons=_unique(lessons)[:6],
                required_verifications=_unique(required_verifications)[:6],
                reliability=_best_reliability(reliabilities),
            )
        )
    return results


def _signal(
    analogy: HistoricalAnalogy,
    signal_type: str,
    strength: str,
    rationale: str,
    reliability: str,
    affected_chain_steps: list[int] | None = None,
    related_assets: list[str] | None = None,
    risk_notes: list[str] | None = None,
) -> CausalValidationSignal:
    return CausalValidationSignal(
        signal_type=signal_type,
        strength=strength,
        source_case_id=analogy.historical_case_id,
        source_case_title=analogy.historical_case_title,
        rationale=rationale,
        affected_chain_steps=affected_chain_steps or [],
        related_assets=related_assets or [],
        reliability=reliability,
        risk_notes=risk_notes or [],
    )


def _overall_validation(signals: list[CausalValidationSignal]) -> tuple[str, float]:
    if not signals:
        return "insufficient_history", 0.0
    if any(signal.signal_type == "weakens_chain" for signal in signals):
        return "historically_weakened", -0.05

    useful = [
        signal
        for signal in signals
        if signal.signal_type not in {"insufficient_evidence"}
    ]
    if useful and all(signal.reliability == "demo_only" for signal in useful):
        if any(signal.signal_type == "supports_chain" for signal in useful):
            return "demo_only", 0.02
        return "demo_only", 0.0

    if any(
        signal.signal_type == "supports_chain"
        and signal.reliability in {"preliminary", "review_backed", "market_backed"}
        for signal in signals
    ):
        if any(signal.reliability in {"review_backed", "market_backed"} for signal in signals):
            return "historically_supported", 0.05
        return "partially_supported", 0.02

    if any(signal.signal_type == "supports_chain" for signal in signals):
        return "partially_supported", 0.02

    if any(signal.signal_type in {"requires_verification", "priced_in_risk", "second_order_warning"} for signal in signals):
        return "mixed_or_inconclusive", -0.03
    return "insufficient_history", 0.0


def _mostly_mismatched(comparison: HistoricalOutcomeComparison) -> bool:
    comparable = [window for window in comparison.window_comparisons if window.direction_match is not None]
    if not comparable:
        return False
    mismatches = sum(1 for window in comparable if window.direction_match is False)
    return mismatches == len(comparable)


def _asset_overlap(asset_name: str, analogy: HistoricalAnalogy, causal_chain: CausalChain) -> bool:
    asset_tokens = _tokens(asset_name)
    if not asset_tokens:
        return False
    historical_corpus = _joined_text(
        [
            analogy.historical_case_title,
            *analogy.similarities,
            *analogy.transferable_lessons,
        ],
        [
            term
            for dimension in analogy.dimension_scores
            for term in dimension.matched_terms
        ],
    )
    current_chain_tokens = _tokens(_joined_text(causal_chain.affected_assets))
    historical_tokens = _tokens(historical_corpus)
    return bool(asset_tokens & historical_tokens) and bool(asset_tokens & (historical_tokens | current_chain_tokens))


def _context_text(
    structured_event: StructuredEvent,
    causal_chain: CausalChain,
    market_mapping: MarketMapping | None,
) -> str:
    mapped = market_mapping.mapped_assets if market_mapping else []
    return _joined_text(
        [
            structured_event.event_title,
            structured_event.summary,
            *structured_event.affected_assets_hint,
            *structured_event.affected_industries,
            *causal_chain.affected_assets,
            causal_chain.rationale,
            *[step.description for step in causal_chain.logic],
            *[asset.asset_name for asset in mapped],
            *[asset.relation for asset in mapped],
            *[asset.rationale for asset in mapped],
        ]
    )


def _matching_chain_steps(causal_chain: CausalChain, terms: list[str]) -> list[int]:
    return [
        step.order
        for step in causal_chain.logic
        if _contains_any(step.description, terms)
    ]


def _second_order_assets(causal_chain: CausalChain, market_mapping: MarketMapping | None) -> list[str]:
    assets = []
    if market_mapping:
        for mapped_asset in market_mapping.mapped_assets:
            text = _joined_text([mapped_asset.asset_name, mapped_asset.relation, mapped_asset.rationale])
            if _contains_any(text, SECOND_ORDER_TERMS + VERIFICATION_TERMS) or mapped_asset.relation == "second_order_watch":
                assets.append(mapped_asset.asset_name)
    if not assets:
        assets.extend(
            asset
            for asset in causal_chain.affected_assets
            if _contains_any(asset, SECOND_ORDER_TERMS)
        )
    return _unique(assets)


def _comparison_reliability(comparison: HistoricalOutcomeComparison | None) -> str:
    if comparison is None:
        return "insufficient"
    return comparison.comparison_reliability or "insufficient"


def _case_risk_notes(reliability: str) -> list[str]:
    notes = []
    if reliability == "demo_only":
        notes.append(DEMO_ONLY_RISK_NOTE)
    notes.append(RESEARCH_RISK_NOTE)
    return notes


def _signal_strength(analogy: HistoricalAnalogy) -> str:
    if analogy.strength_label == "strong":
        return "strong"
    if analogy.strength_label == "moderate":
        return "moderate"
    return "weak"


def _best_reliability(reliabilities: Iterable[str]) -> str:
    values = list(reliabilities)
    if not values:
        return "insufficient"
    return max(values, key=lambda value: RELIABILITY_RANK.get(value, 0))


def _contains_any(value: str, terms: list[str]) -> bool:
    text = value.casefold()
    return any(term.casefold() in text for term in terms)


def _joined_text(*groups: Iterable[str]) -> str:
    values = []
    for group in groups:
        values.extend(str(value) for value in group if value)
    return " ".join(values)


def _tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", str(value).casefold())
    return {token for token in normalized.split() if len(token) >= 2}


def _dedupe_signals(signals: list[CausalValidationSignal]) -> list[CausalValidationSignal]:
    results: list[CausalValidationSignal] = []
    seen: set[tuple[str, str | None, str]] = set()
    for signal in signals:
        key = (signal.signal_type, signal.source_case_id, signal.rationale)
        if key in seen:
            continue
        seen.add(key)
        results.append(signal)
    return results


def _unique(values: Iterable[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
