"""Historical case store utilities for EventAlpha."""

from .analogy import AnalogyDimensionScore, HistoricalAnalogy, make_analogy_id
from .analogy_explainer import HistoricalAnalogyExplainer
from .analogy_retriever import (
    HistoricalAnalogyRetriever,
    retrieve_analogies_for_query,
    retrieve_analogies_for_structured_event,
    retrieve_analogies_for_tracked_event,
)
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
    "AnalogyDimensionScore",
    "DEFAULT_HISTORICAL_CASE_STORE_PATH",
    "HistoricalAnalogy",
    "HistoricalAnalogyExplainer",
    "HistoricalAnalogyRetriever",
    "HistoricalCase",
    "HistoricalCaseSearch",
    "HistoricalCaseStore",
    "HistoricalCausalAssessment",
    "HistoricalOutcome",
    "build_seed_historical_cases",
    "make_analogy_id",
    "make_historical_case_id",
    "retrieve_analogies_for_query",
    "retrieve_analogies_for_structured_event",
    "retrieve_analogies_for_tracked_event",
    "search_cases",
    "search_cases_for_structured_event",
    "search_cases_for_tracked_event",
    "summarize_case",
    "summarize_search_results",
]
