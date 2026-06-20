"""Historical case store utilities for EventAlpha."""

from .case_search import (
    HistoricalCaseSearch,
    search_cases,
    search_cases_for_structured_event,
    search_cases_for_tracked_event,
)
from .case_store import DEFAULT_HISTORICAL_CASE_STORE_PATH, HistoricalCaseStore
from .case_summary import summarize_case, summarize_search_results
from .schemas import (
    HistoricalCase,
    HistoricalCausalAssessment,
    HistoricalOutcome,
    make_historical_case_id,
)
from .seed_cases import build_seed_historical_cases

__all__ = [
    "DEFAULT_HISTORICAL_CASE_STORE_PATH",
    "HistoricalCase",
    "HistoricalCaseSearch",
    "HistoricalCaseStore",
    "HistoricalCausalAssessment",
    "HistoricalOutcome",
    "build_seed_historical_cases",
    "make_historical_case_id",
    "search_cases",
    "search_cases_for_structured_event",
    "search_cases_for_tracked_event",
    "summarize_case",
    "summarize_search_results",
]
