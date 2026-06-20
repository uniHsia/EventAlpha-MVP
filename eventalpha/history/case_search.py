"""Rule-based historical case search."""

from __future__ import annotations

import re
from collections.abc import Iterable

from eventalpha.news import TrackedEvent
from eventalpha.schemas import StructuredEvent

from .case_store import HistoricalCaseStore
from .schemas import HistoricalCase


def search_cases(
    cases: Iterable[HistoricalCase],
    query: str | None = None,
    event_type: str | None = None,
    assets: list[str] | None = None,
    entities: list[str] | None = None,
    tags: list[str] | None = None,
    limit: int = 5,
) -> list[HistoricalCase]:
    """Search cases with deterministic keyword and overlap scoring."""
    scored: list[tuple[float, HistoricalCase]] = []
    for historical_case in cases:
        score = _score_case(
            historical_case,
            query=query,
            event_type=event_type,
            assets=assets or [],
            entities=entities or [],
            tags=tags or [],
        )
        if score > 0:
            scored.append((score, historical_case))
    scored.sort(key=lambda item: (item[0], _completeness(item[1]), item[1].event_date or ""), reverse=True)
    return [historical_case for _, historical_case in scored[: max(limit, 0)]]


def search_cases_for_tracked_event(
    cases: Iterable[HistoricalCase],
    tracked_event: TrackedEvent,
    limit: int = 5,
) -> list[HistoricalCase]:
    """Build search terms from a TrackedEvent."""
    query_parts = [tracked_event.canonical_title, tracked_event.current_summary or ""]
    query_parts.extend(tracked_event.latest_claims)
    return search_cases(
        cases,
        query=" ".join(query_parts),
        assets=tracked_event.dominant_keywords,
        entities=tracked_event.sources,
        tags=tracked_event.dominant_keywords,
        limit=limit,
    )


def search_cases_for_structured_event(
    cases: Iterable[HistoricalCase],
    event: StructuredEvent,
    limit: int = 5,
) -> list[HistoricalCase]:
    """Build search terms from a StructuredEvent."""
    return search_cases(
        cases,
        query=f"{event.event_title} {event.summary}",
        event_type=event.event_type,
        assets=event.affected_assets_hint + event.affected_industries,
        entities=event.entities,
        tags=[event.event_type],
        limit=limit,
    )


class HistoricalCaseSearch:
    """Convenience wrapper around list/store-backed case search."""

    def __init__(self, store_or_cases: HistoricalCaseStore | Iterable[HistoricalCase]) -> None:
        self.store_or_cases = store_or_cases

    def search(
        self,
        query: str | None = None,
        event_type: str | None = None,
        assets: list[str] | None = None,
        entities: list[str] | None = None,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[HistoricalCase]:
        """Search cases from a store or iterable."""
        cases = (
            self.store_or_cases.list_cases()
            if isinstance(self.store_or_cases, HistoricalCaseStore)
            else list(self.store_or_cases)
        )
        return search_cases(
            cases,
            query=query,
            event_type=event_type,
            assets=assets,
            entities=entities,
            tags=tags,
            limit=limit,
        )


def _score_case(
    historical_case: HistoricalCase,
    query: str | None,
    event_type: str | None,
    assets: list[str],
    entities: list[str],
    tags: list[str],
) -> float:
    score = 0.0
    if event_type and historical_case.event_type == event_type:
        score += 8.0
    score += 3.0 * _overlap_score(assets, historical_case.affected_assets + historical_case.industries)
    score += 2.5 * _overlap_score(entities, historical_case.entities)
    score += 2.0 * _overlap_score(tags, historical_case.tags)
    if query:
        query_tokens = _tokens(query)
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
        score += 4.0 * _jaccard(query_tokens, case_tokens)
        score += float(len(query_tokens & case_tokens))
    return score


def _overlap_score(left: list[str], right: list[str]) -> float:
    left_tokens = set().union(*(_tokens(value) for value in left)) if left else set()
    right_tokens = set().union(*(_tokens(value) for value in right)) if right else set()
    return _jaccard(left_tokens, right_tokens)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value).casefold())
        if len(token) >= 2
    }


def _completeness(historical_case: HistoricalCase) -> int:
    score = 0
    if historical_case.outcome:
        score += 1
    if historical_case.causal_assessment and historical_case.causal_assessment.lessons:
        score += 1
    return score
