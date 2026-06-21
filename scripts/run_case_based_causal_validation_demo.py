"""Run the Phase 5D case-based causal validation demo."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import (  # noqa: E402
    extract_event,
    generate_causal_chain,
    map_event_to_markets,
    score_event,
    verify_event,
)
from eventalpha.history import (  # noqa: E402
    CaseBasedCausalValidationReportBuilder,
    CaseBasedCausalValidator,
    DEFAULT_HISTORICAL_CASE_STORE_PATH,
    HistoricalAnalogyRetriever,
    HistoricalCase,
    HistoricalCaseStore,
    HistoricalOutcomeComparator,
    build_demo_current_ai_export_context,
    build_seed_historical_cases,
)
from eventalpha.schemas import RISK_DISCLAIMER, RawNews  # noqa: E402


def run_case_based_causal_validation_demo(
    demo_current_ai_export: bool = False,
    mock_outcome_scenario: str = "aligned",
    limit: int = 3,
    store_path: str | Path = DEFAULT_HISTORICAL_CASE_STORE_PATH,
) -> dict[str, Any]:
    """Run an offline case-based causal validation demo."""
    raw_news = _demo_raw_news(demo_current_ai_export)
    structured_event = extract_event(raw_news)
    verification = verify_event(raw_news, structured_event)
    impact_score = score_event(structured_event, verification)
    causal_chain = generate_causal_chain(structured_event, impact_score)
    market_mapping = map_event_to_markets(structured_event, causal_chain)

    store = HistoricalCaseStore(store_path).load()
    seed_cases = build_seed_historical_cases()
    cases, refreshed_seed_outcomes = _refresh_zero_seed_outcomes(store.list_cases(), seed_cases)
    if not cases:
        cases = seed_cases
    case_by_id = {case.case_id: case for case in cases}

    context = _analogy_context(structured_event, causal_chain, demo_current_ai_export)
    analogies = HistoricalAnalogyRetriever(cases).retrieve(limit=limit, **context)
    current_market_returns = _build_mock_current_outcome(mock_outcome_scenario)
    comparator = HistoricalOutcomeComparator()
    comparisons = [
        comparator.compare(
            analogy=analogy,
            historical_case=case_by_id[analogy.historical_case_id],
            current_market_returns=current_market_returns,
            current_data_quality="mock_demo",
            scenario_name=mock_outcome_scenario,
        )
        for analogy in analogies
        if analogy.historical_case_id in case_by_id
    ]
    validation = CaseBasedCausalValidator().validate(
        structured_event=structured_event,
        causal_chain=causal_chain,
        market_mapping=market_mapping,
        analogies=analogies,
        outcome_comparisons=comparisons,
    )
    report = CaseBasedCausalValidationReportBuilder().build_text_report(validation)
    return {
        "raw_news": raw_news,
        "structured_event": structured_event,
        "verification": verification,
        "impact_score": impact_score,
        "causal_chain": causal_chain,
        "market_mapping": market_mapping,
        "cases": cases,
        "used_seed_memory": not bool(store.list_cases()),
        "refreshed_seed_outcomes": refreshed_seed_outcomes,
        "analogies": analogies,
        "comparisons": comparisons,
        "validation": validation,
        "report": report,
        "current_market_returns": current_market_returns,
        "mock_outcome_scenario": mock_outcome_scenario,
    }


def _demo_raw_news(demo_current_ai_export: bool) -> RawNews:
    if demo_current_ai_export:
        return RawNews(
            title="US expands AI chip export controls",
            source="Reuters",
            source_type="mainstream_media",
            language="en",
            raw_text=(
                "The US announced expanded export controls on advanced AI chips and GPUs. "
                "The restrictions may affect overseas GPU supply and raise attention on domestic "
                "AI chip substitutes, semiconductor equipment, advanced packaging, and EDA tools."
            ),
        )
    data = json.loads((ROOT / "eventalpha" / "examples" / "demo_events.json").read_text(encoding="utf-8"))
    return RawNews(**data[0])


def _analogy_context(structured_event, causal_chain, demo_current_ai_export: bool) -> dict[str, Any]:
    if demo_current_ai_export:
        context = build_demo_current_ai_export_context()
        context["query"] = structured_event.event_title
        return context
    return {
        "query": f"{structured_event.event_title} {structured_event.summary}",
        "event_type": structured_event.event_type,
        "assets": structured_event.affected_assets_hint,
        "entities": structured_event.entities,
        "industries": structured_event.affected_industries,
        "tags": [structured_event.event_type],
        "causal_chain": [step.description for step in causal_chain.logic],
    }


def _refresh_zero_seed_outcomes(
    cases: list[HistoricalCase],
    seed_cases: list[HistoricalCase],
) -> tuple[list[HistoricalCase], bool]:
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
    print("EventAlpha-MVP Case-Based Causal Validation Demo")
    print(f"Current event: {result['structured_event'].event_title}")
    print(f"Analogies: {len(result['analogies'])}")
    print(f"Comparisons: {len(result['comparisons'])}")
    print(f"Mock outcome scenario: {result['mock_outcome_scenario']} (deterministic demo data, not real market data)")
    if result["used_seed_memory"]:
        print("Store not populated; using in-memory MVP seed cases.")
    if result["refreshed_seed_outcomes"]:
        print("Loaded store had older all-zero manual seed outcomes; using current seed demo returns in memory.")
    print()
    print(result["report"])


def main() -> None:
    """Run the case-based causal validation CLI."""
    parser = ArgumentParser(description="Validate current causal chains against historical analogies.")
    parser.add_argument("--demo-current-ai-export", action="store_true", help="Use the rich AI export-control context.")
    parser.add_argument(
        "--mock-outcome-scenario",
        choices=["aligned", "mixed", "opposite"],
        default="aligned",
        help="Deterministic mock current outcome scenario.",
    )
    parser.add_argument("--limit", type=int, default=3, help="Maximum historical analogies to use.")
    parser.add_argument("--store-path", default=str(DEFAULT_HISTORICAL_CASE_STORE_PATH), help="Historical case JSON path.")
    args = parser.parse_args()

    result = run_case_based_causal_validation_demo(
        demo_current_ai_export=args.demo_current_ai_export,
        mock_outcome_scenario=args.mock_outcome_scenario,
        limit=args.limit,
        store_path=args.store_path,
    )
    _print_result(result)
    if RISK_DISCLAIMER not in result["report"]:
        print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
