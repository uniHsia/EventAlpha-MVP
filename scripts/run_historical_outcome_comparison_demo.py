"""Run the Phase 5C historical outcome comparison demo."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.history import (  # noqa: E402
    DEFAULT_HISTORICAL_CASE_STORE_PATH,
    HistoricalAnalogyRetriever,
    HistoricalCaseStore,
    HistoricalOutcomeComparator,
    HistoricalOutcomeReportBuilder,
    build_demo_current_ai_export_context,
    build_seed_historical_cases,
)
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402


def run_historical_outcome_comparison_demo(
    query: str | None = None,
    demo_current_ai_export: bool = False,
    limit: int = 3,
    store_path: str | Path = DEFAULT_HISTORICAL_CASE_STORE_PATH,
    with_mock_current_outcome: bool = False,
) -> dict[str, Any]:
    """Retrieve analogies and compare historical/current outcomes."""
    store = HistoricalCaseStore(store_path).load()
    cases = store.list_cases() if store.list_cases() else build_seed_historical_cases()
    case_by_id = {case.case_id: case for case in cases}
    retriever = HistoricalAnalogyRetriever(cases)
    context: dict[str, Any] = {"query": query or "AI chip export control"}
    if demo_current_ai_export:
        context = build_demo_current_ai_export_context()

    analogies = retriever.retrieve(limit=limit, **context)
    comparator = HistoricalOutcomeComparator()
    current_market_returns = _build_mock_current_outcome() if with_mock_current_outcome else {}
    comparisons = [
        comparator.compare(
            analogy=analogy,
            historical_case=case_by_id[analogy.historical_case_id],
            current_market_returns=current_market_returns,
        )
        for analogy in analogies
        if analogy.historical_case_id in case_by_id
    ]
    report = HistoricalOutcomeReportBuilder().build_text_report(comparisons)
    return {
        "store": store,
        "used_seed_memory": not bool(store.list_cases()),
        "cases": cases,
        "analogies": analogies,
        "comparisons": comparisons,
        "report": report,
        "current_market_returns": current_market_returns,
    }


def _build_mock_current_outcome() -> dict[str, dict[str, float]]:
    """Build deterministic flat mock current outcome for seed-demo comparison."""
    return {
        "T+1": {"actual_return": 0.0, "benchmark_return": 0.0, "excess_return": 0.0},
        "T+3": {"actual_return": 0.0, "benchmark_return": 0.0, "excess_return": 0.0},
        "T+7": {"actual_return": 0.0, "benchmark_return": 0.0, "excess_return": 0.0},
    }


def _print_result(result: dict[str, Any]) -> None:
    print("EventAlpha-MVP Historical Outcome Comparison Demo")
    print(f"Available cases: {len(result['cases'])}")
    print(f"Analogies: {len(result['analogies'])}")
    print(f"Comparisons: {len(result['comparisons'])}")
    if result["used_seed_memory"]:
        print("Store not populated; using in-memory MVP seed cases.")
    if result["current_market_returns"]:
        print("Using mock current outcome for deterministic comparison.")
    print()
    print(result["report"])


def main() -> None:
    """Run the outcome comparison demo CLI."""
    parser = ArgumentParser(description="Compare historical analogy outcomes with current outcomes.")
    parser.add_argument("--query", default=None, help="Keyword query.")
    parser.add_argument("--demo-current-ai-export", action="store_true", help="Use the rich AI export-control context.")
    parser.add_argument("--limit", type=int, default=3, help="Maximum comparisons to show.")
    parser.add_argument("--store-path", default=str(DEFAULT_HISTORICAL_CASE_STORE_PATH), help="Historical case JSON path.")
    parser.add_argument("--with-mock-current-outcome", action="store_true", help="Use deterministic mock current returns.")
    args = parser.parse_args()

    result = run_historical_outcome_comparison_demo(
        query=args.query,
        demo_current_ai_export=args.demo_current_ai_export,
        limit=args.limit,
        store_path=args.store_path,
        with_mock_current_outcome=args.with_mock_current_outcome,
    )
    _print_result(result)
    if RISK_DISCLAIMER not in result["report"]:
        print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
