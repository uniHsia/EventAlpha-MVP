"""Rule-based historical analogy retrieval."""

from __future__ import annotations

import re
from collections.abc import Iterable

from eventalpha.news import TrackedEvent
from eventalpha.schemas import StructuredEvent

from .analogy import AnalogyDimensionScore, HistoricalAnalogy
from .schemas import HistoricalCase


DIMENSION_WEIGHTS = {
    "event_type": 0.20,
    "affected_assets": 0.20,
    "entities": 0.14,
    "industries": 0.12,
    "tags": 0.10,
    "causal_chain": 0.10,
    "query_keywords": 0.10,
    "region": 0.04,
}


class HistoricalAnalogyRetriever:
    """Retrieve and explain historical analogies with deterministic rules."""

    def __init__(self, cases: Iterable[HistoricalCase]) -> None:
        self.cases = list(cases)

    def retrieve(
        self,
        query: str | None = None,
        event_type: str | None = None,
        assets: list[str] | None = None,
        entities: list[str] | None = None,
        industries: list[str] | None = None,
        tags: list[str] | None = None,
        region: str | None = None,
        causal_chain: list[str] | None = None,
        limit: int = 5,
    ) -> list[HistoricalAnalogy]:
        """Return top historical analogies."""
        current_title = query or event_type or "current event"
        analogies = [
            self._build_analogy(
                historical_case,
                current_event_title=current_title,
                query=query,
                event_type=event_type,
                assets=assets or [],
                entities=entities or [],
                industries=industries or [],
                tags=tags or [],
                region=region,
                causal_chain=causal_chain or [],
            )
            for historical_case in self.cases
        ]
        analogies = [analogy for analogy in analogies if analogy.overall_score > 0]
        analogies.sort(key=lambda analogy: analogy.overall_score, reverse=True)
        return analogies[: max(limit, 0)]

    def _build_analogy(
        self,
        historical_case: HistoricalCase,
        current_event_title: str,
        query: str | None,
        event_type: str | None,
        assets: list[str],
        entities: list[str],
        industries: list[str],
        tags: list[str],
        region: str | None,
        causal_chain: list[str],
    ) -> HistoricalAnalogy:
        dimension_scores = [
            _exact_dimension("event_type", event_type, historical_case.event_type),
            _overlap_dimension("affected_assets", assets, historical_case.affected_assets),
            _overlap_dimension("entities", entities, historical_case.entities),
            _overlap_dimension("industries", industries, historical_case.industries),
            _overlap_dimension("tags", tags, historical_case.tags),
            _overlap_dimension("causal_chain", causal_chain, historical_case.causal_chain_summary),
            _query_dimension(query, historical_case),
            _exact_dimension("region", region, historical_case.region),
        ]
        overall = sum(score.score * DIMENSION_WEIGHTS[score.dimension] for score in dimension_scores)
        similarities = _similarities(dimension_scores)
        differences = _differences(dimension_scores, historical_case, event_type, region)
        transferable_lessons = _transferable_lessons(historical_case)
        non_transferable_lessons = _non_transferable_lessons(historical_case)
        verification_suggestions = _verification_suggestions(dimension_scores, historical_case)
        risk_notes = _risk_notes(historical_case)
        return HistoricalAnalogy(
            current_event_title=current_event_title,
            historical_case_id=historical_case.case_id,
            historical_case_title=historical_case.title,
            overall_score=overall,
            dimension_scores=dimension_scores,
            similarities=similarities,
            differences=differences,
            transferable_lessons=transferable_lessons,
            non_transferable_lessons=non_transferable_lessons,
            verification_suggestions=verification_suggestions,
            risk_notes=risk_notes,
        )


def retrieve_analogies_for_query(
    query: str,
    cases: Iterable[HistoricalCase],
    limit: int = 5,
) -> list[HistoricalAnalogy]:
    """Retrieve analogies from a free-text query."""
    return HistoricalAnalogyRetriever(cases).retrieve(query=query, limit=limit)


def retrieve_analogies_for_structured_event(
    event: StructuredEvent,
    cases: Iterable[HistoricalCase],
    limit: int = 5,
) -> list[HistoricalAnalogy]:
    """Retrieve analogies from a StructuredEvent."""
    return HistoricalAnalogyRetriever(cases).retrieve(
        query=f"{event.event_title} {event.summary}",
        event_type=event.event_type,
        assets=event.affected_assets_hint,
        entities=event.entities,
        industries=event.affected_industries,
        tags=[event.event_type],
        causal_chain=[event.summary],
        limit=limit,
    )


def retrieve_analogies_for_tracked_event(
    event: TrackedEvent,
    cases: Iterable[HistoricalCase],
    limit: int = 5,
) -> list[HistoricalAnalogy]:
    """Retrieve analogies from a TrackedEvent."""
    return HistoricalAnalogyRetriever(cases).retrieve(
        query=" ".join([event.canonical_title, event.current_summary or "", *event.latest_claims]),
        assets=event.dominant_keywords,
        entities=event.sources,
        tags=event.dominant_keywords,
        causal_chain=event.latest_claims,
        limit=limit,
    )


def _exact_dimension(dimension: str, current: str | None, historical: str | None) -> AnalogyDimensionScore:
    current_norm = _normalize(current)
    historical_norm = _normalize(historical)
    score = 1.0 if current_norm and current_norm == historical_norm else 0.0
    matched_terms = [historical] if score and historical else []
    explanation = f"{dimension} exact match." if score else f"{dimension} did not match exactly."
    return AnalogyDimensionScore(
        dimension=dimension,
        score=score,
        matched_terms=matched_terms,
        explanation=explanation,
    )


def _overlap_dimension(dimension: str, current: list[str], historical: list[str]) -> AnalogyDimensionScore:
    current_tokens = _tokens_from_values(current)
    historical_tokens = _tokens_from_values(historical)
    matched = sorted(current_tokens & historical_tokens)
    score = _jaccard(current_tokens, historical_tokens)
    explanation = (
        f"{dimension} matched terms: {', '.join(matched)}."
        if matched
        else f"{dimension} had no material overlap."
    )
    return AnalogyDimensionScore(
        dimension=dimension,
        score=score,
        matched_terms=matched,
        explanation=explanation,
    )


def _query_dimension(query: str | None, historical_case: HistoricalCase) -> AnalogyDimensionScore:
    query_tokens = _tokens(query or "")
    case_tokens = _tokens(
        " ".join(
            [
                historical_case.title,
                historical_case.summary,
                historical_case.event_type,
                " ".join(historical_case.entities),
                " ".join(historical_case.industries),
                " ".join(historical_case.affected_assets),
                " ".join(historical_case.tags),
            ]
        )
    )
    matched = sorted(query_tokens & case_tokens)
    score = (len(matched) / len(query_tokens)) if query_tokens else 0.0
    return AnalogyDimensionScore(
        dimension="query_keywords",
        score=score,
        matched_terms=matched,
        explanation=(
            f"Query matched: {', '.join(matched)}."
            if matched
            else "Query had no material keyword overlap."
        ),
    )


def _similarities(dimension_scores: list[AnalogyDimensionScore]) -> list[str]:
    similarities = [
        f"{score.dimension} overlap: {', '.join(score.matched_terms)}"
        for score in dimension_scores
        if score.score >= 0.3 and score.matched_terms
    ]
    return similarities or ["Only weak surface-level similarity was detected."]


def _differences(
    dimension_scores: list[AnalogyDimensionScore],
    historical_case: HistoricalCase,
    event_type: str | None,
    region: str | None,
) -> list[str]:
    differences = []
    low_dimensions = [score.dimension for score in dimension_scores if score.dimension in {"affected_assets", "entities", "industries"} and score.score == 0]
    if low_dimensions:
        differences.append(f"Low overlap in key dimensions: {', '.join(low_dimensions)}.")
    if event_type and event_type != historical_case.event_type:
        differences.append(f"Historical event type was {historical_case.event_type}, not {event_type}.")
    if region and historical_case.region and _normalize(region) != _normalize(historical_case.region):
        differences.append(f"Historical region was {historical_case.region}, not {region}.")
    if historical_case.outcome and historical_case.outcome.outcome_quality == "manual_seed_demo":
        differences.append("Historical outcome is an MVP manual seed, not a verified return study.")
    return differences or ["No major rule-based difference was detected, but manual review is still required."]


def _transferable_lessons(historical_case: HistoricalCase) -> list[str]:
    lessons = []
    if historical_case.causal_assessment:
        lessons.extend(historical_case.causal_assessment.lessons)
    lessons.extend(
        [
            "Separate direct impact from second-order market mapping.",
            "Check whether the market has already priced in the event.",
        ]
    )
    return _unique(lessons)[:5]


def _non_transferable_lessons(historical_case: HistoricalCase) -> list[str]:
    notes = [
        "Historical market reaction cannot be mechanically reused for the current event.",
        "Current verification status, policy details, and market positioning may differ.",
    ]
    if historical_case.outcome and historical_case.outcome.outcome_quality == "manual_seed_demo":
        notes.append("Seed outcome is illustrative demo data, not verified backtest evidence.")
    return notes


def _verification_suggestions(
    dimension_scores: list[AnalogyDimensionScore],
    historical_case: HistoricalCase,
) -> list[str]:
    suggestions = [
        "Check official announcements and primary policy documents.",
        "Verify whether the market reaction was already priced in.",
    ]
    matched_terms = {term for score in dimension_scores for term in score.matched_terms}
    case_text = " ".join([historical_case.title, historical_case.summary, " ".join(historical_case.tags)]).casefold()
    if {"ai", "chip", "gpu", "semiconductor"} & matched_terms or "chip" in case_text:
        suggestions.append("Check GPU orders, cloud capex, export-control details, and semiconductor supply-chain indicators.")
    if {"oil", "shipping", "red"} & matched_terms or "oil" in case_text or "shipping" in case_text:
        suggestions.append("Check supply disruption evidence, shipping rerouting, inventory, and freight-rate indicators.")
    if "rate" in case_text or "central" in case_text:
        suggestions.append("Check central-bank guidance, yield curve moves, FX reaction, and macro data confirmation.")
    return _unique(suggestions)[:6]


def _risk_notes(historical_case: HistoricalCase) -> list[str]:
    notes = ["Historical analogies are research aids and do not constitute investment advice."]
    if historical_case.outcome and historical_case.outcome.outcome_quality == "manual_seed_demo":
        notes.append("The historical outcome is illustrative seed data, not a verified market return.")
    return notes


def _tokens_from_values(values: list[str]) -> set[str]:
    return set().union(*(_tokens(value) for value in values)) if values else set()


def _tokens(value: str) -> set[str]:
    return {
        _normalize_token(token)
        for token in re.findall(r"[a-z0-9]+", str(value).casefold())
        if len(token) >= 2
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _normalize_token(token: str) -> str:
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _unique(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
