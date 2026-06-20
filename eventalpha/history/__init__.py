"""Historical case store utilities for EventAlpha."""

from .analogy import (
    AnalogyDimensionScore,
    AnalogyInputContext,
    HistoricalAnalogy,
    analogy_strength_label,
    make_analogy_id,
)
from .analogy_explainer import HistoricalAnalogyExplainer
from .analogy_retriever import (
    HistoricalAnalogyRetriever,
    build_demo_current_ai_export_context,
    build_input_context,
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
from .outcome_comparison import (
    DEFAULT_OUTCOME_WINDOWS,
    HistoricalCurrentOutcomePair,
    HistoricalOutcomeComparison,
    OutcomeWindowComparison,
    make_outcome_comparison_id,
)
from .outcome_comparator import HistoricalOutcomeComparator
from .outcome_report import HistoricalOutcomeReportBuilder
from .schemas import (
    HistoricalCase,
    HistoricalCausalAssessment,
    HistoricalOutcome,
    make_historical_case_id,
)
from .seed_cases import build_seed_historical_cases

__all__ = [
    "AnalogyDimensionScore",
    "AnalogyInputContext",
    "DEFAULT_HISTORICAL_CASE_STORE_PATH",
    "DEFAULT_OUTCOME_WINDOWS",
    "HistoricalAnalogy",
    "HistoricalAnalogyExplainer",
    "HistoricalAnalogyRetriever",
    "HistoricalCase",
    "HistoricalCaseSearch",
    "HistoricalCaseStore",
    "HistoricalCausalAssessment",
    "HistoricalCurrentOutcomePair",
    "HistoricalOutcome",
    "HistoricalOutcomeComparator",
    "HistoricalOutcomeComparison",
    "HistoricalOutcomeReportBuilder",
    "OutcomeWindowComparison",
    "analogy_strength_label",
    "build_demo_current_ai_export_context",
    "build_input_context",
    "build_seed_historical_cases",
    "make_analogy_id",
    "make_historical_case_id",
    "make_outcome_comparison_id",
    "retrieve_analogies_for_query",
    "retrieve_analogies_for_structured_event",
    "retrieve_analogies_for_tracked_event",
    "search_cases",
    "search_cases_for_structured_event",
    "search_cases_for_tracked_event",
    "summarize_case",
    "summarize_search_results",
]
