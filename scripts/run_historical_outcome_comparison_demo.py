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
    HistoricalCase,
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
    mock_outcome_scenario: str = "aligned",
) -> dict[str, Any]:
    """Retrieve analogies and compare historical/current outcomes."""
    store = HistoricalCaseStore(store_path).load()
    seed_cases = build_seed_historical_cases()
    raw_cases = store.list_cases()
    cases, refreshed_seed_outcomes = _refresh_zero_seed_outcomes(raw_cases, seed_cases)
    if not cases:
        cases = seed_cases
    case_by_id = {case.case_id: case for case in cases}
    retriever = HistoricalAnalogyRetriever(cases)
    context: dict[str, Any] = {"query": query or "AI chip export control"}
    if demo_current_ai_export:
        context = build_demo_current_ai_export_context()

    analogies = retriever.retrieve(limit=limit, **context)
    comparator = HistoricalOutcomeComparator()
    current_market_returns = (
        _build_mock_current_outcome(mock_outcome_scenario)
        if with_mock_current_outcome
        else {}
    )
    comparisons = [
        comparator.compare(
            analogy=analogy,
            historical_case=case_by_id[analogy.historical_case_id],
            current_market_returns=current_market_returns,
            current_data_quality="mock_demo" if with_mock_current_outcome else None,
            scenario_name=mock_outcome_scenario if with_mock_current_outcome else None,
        )
        for analogy in analogies
        if analogy.historical_case_id in case_by_id
    ]
    report = HistoricalOutcomeReportBuilder().build_text_report(comparisons)
    return {
        "store": store,
        "used_seed_memory": not bool(store.list_cases()),
        "refreshed_seed_outcomes": refreshed_seed_outcomes,
        "cases": cases,
        "analogies": analogies,
        "comparisons": comparisons,
        "report": report,
        "current_market_returns": current_market_returns,
        "mock_outcome_scenario": mock_outcome_scenario if with_mock_current_outcome else None,
    }


def _refresh_zero_seed_outcomes(
    cases: list[HistoricalCase],
    seed_cases: list[HistoricalCase],
) -> tuple[list[HistoricalCase], bool]:
    """Use current seed returns when an old manual seed store still has all-zero outcomes."""
    seed_by_id = {case.case_id: case for case in seed_cases}
    refreshed = False
    results: list[HistoricalCase] = []
    for historical_case in cases:
        seed_case = seed_by_id.get(historical_case.case_id)
        if seed_case and _has_all_zero_manual_seed_returns(historical_case):
            results.append(seed_case)
            refreshed = True
        else:
            results.append(historical_case)
    return results, refreshed


def _has_all_zero_manual_seed_returns(historical_case: HistoricalCase) -> bool:
    outcome = historical_case.outcome
    if not outcome or outcome.outcome_quality != "manual_seed_demo":
        return False
    values = [
        value
        for returns in outcome.asset_returns.values()
        for value in returns.values()
        if value is not None
    ]
    return bool(values) and all(float(value) == 0.0 for value in values)


def _build_mock_current_outcome(scenario: str = "aligned") -> dict[str, dict[str, float]]:
    """Build deterministic demo current outcomes without market data access."""
    scenarios = {
        "aligned": {
            "T+1": {"actual_return": 0.011, "benchmark_return": 0.002, "excess_return": 0.009},
            "T+3": {"actual_return": 0.024, "benchmark_return": 0.004, "excess_return": 0.020},
            "T+7": {"actual_return": 0.014, "benchmark_return": 0.003, "excess_return": 0.011},
        },
        "mixed": {
            "T+1": {"actual_return": 0.010, "benchmark_return": 0.002, "excess_return": 0.008},
            "T+3": {"actual_return": -0.009, "benchmark_return": 0.001, "excess_return": -0.010},
            "T+7": {"actual_return": -0.004, "benchmark_return": 0.002, "excess_return": -0.006},
        },
        "opposite": {
            "T+1": {"actual_return": -0.011, "benchmark_return": 0.002, "excess_return": -0.013},
            "T+3": {"actual_return": -0.024, "benchmark_return": 0.004, "excess_return": -0.028},
            "T+7": {"actual_return": -0.014, "benchmark_return": 0.003, "excess_return": -0.017},
        },
    }
    if scenario not in scenarios:
        raise ValueError(f"Unsupported mock outcome scenario: {scenario}")
    return scenarios[scenario]


def _print_result(result: dict[str, Any]) -> None:
    print("EventAlpha-MVP Historical Outcome Comparison Demo")
    print(f"Available cases: {len(result['cases'])}")
    print(f"Analogies: {len(result['analogies'])}")
    print(f"Comparisons: {len(result['comparisons'])}")
    if result["used_seed_memory"]:
        print("Store not populated; using in-memory MVP seed cases.")
    if result["refreshed_seed_outcomes"]:
        print("Loaded store had older all-zero manual seed outcomes; using current seed demo returns in memory.")
    if result["current_market_returns"]:
        print(
            "Using deterministic mock current outcome "
            f"scenario={result['mock_outcome_scenario']}; this is demo data, not real market data."
        )
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
    parser.add_argument(
        "--mock-outcome-scenario",
        choices=["aligned", "mixed", "opposite"],
        default="aligned",
        help="Deterministic mock outcome scenario to use with --with-mock-current-outcome.",
    )
    args = parser.parse_args()

    result = run_historical_outcome_comparison_demo(
        query=args.query,
        demo_current_ai_export=args.demo_current_ai_export,
        limit=args.limit,
        store_path=args.store_path,
        with_mock_current_outcome=args.with_mock_current_outcome,
        mock_outcome_scenario=args.mock_outcome_scenario,
    )
    _print_result(result)
    if RISK_DISCLAIMER not in result["report"]:
        print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
