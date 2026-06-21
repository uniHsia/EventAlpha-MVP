"""Run an EventCard and AntiSpurious demo with Phase 5D history validation."""

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
    HistoryValidationSummary,
)
from eventalpha.orchestration import run_event_pipeline  # noqa: E402
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402
from scripts.run_case_based_causal_validation_demo import (  # noqa: E402
    _demo_raw_news,
    run_case_based_causal_validation_demo,
)


def run_event_with_history_validation_demo(
    demo_current_ai_export: bool = False,
    mock_outcome_scenario: str = "aligned",
    store_path: str | Path = DEFAULT_HISTORICAL_CASE_STORE_PATH,
) -> dict[str, Any]:
    """Run baseline and history-enhanced event analysis offline."""
    raw_news = _demo_raw_news(demo_current_ai_export)
    baseline = run_event_pipeline(raw_news, persist=False)
    history_result = run_case_based_causal_validation_demo(
        demo_current_ai_export=demo_current_ai_export,
        mock_outcome_scenario=mock_outcome_scenario,
        store_path=store_path,
    )
    summary = HistoryValidationSummary.from_validation(history_result["validation"])
    enhanced = run_event_pipeline(
        raw_news,
        persist=False,
        history_validation_summary=summary,
    )
    return {
        "raw_news": raw_news,
        "baseline": baseline,
        "history_validation": history_result["validation"],
        "history_validation_summary": summary,
        "enhanced": enhanced,
        "mock_outcome_scenario": mock_outcome_scenario,
    }


def _print_result(result: dict[str, Any]) -> None:
    baseline_card = result["baseline"]["event_card"]
    enhanced_card = result["enhanced"]["event_card"]
    baseline_check = result["baseline"]["anti_spurious_check"]
    enhanced_check = result["enhanced"]["anti_spurious_check"]
    summary = result["history_validation_summary"]

    print("EventAlpha-MVP Event + History Validation Demo")
    print(f"Current event: {result['enhanced']['structured_event'].event_title}")
    print(f"Mock outcome scenario: {result['mock_outcome_scenario']} (deterministic demo data, not real market data)")
    print(f"history_overall_validation={summary.overall_validation}")
    print(f"history_reliability={summary.reliability}")
    print(f"history_confidence_adjustment_hint={summary.confidence_adjustment_hint:.4f}")
    print()
    print("Baseline EventCard risk_factors:")
    _print_list(baseline_card.risk_factors)
    print("Enhanced EventCard risk_factors:")
    _print_list(enhanced_card.risk_factors)
    print("Baseline EventCard verification_indicators:")
    _print_list(baseline_card.verification_indicators)
    print("Enhanced EventCard verification_indicators:")
    _print_list(enhanced_card.verification_indicators)
    print()
    print("Baseline AntiSpurious:")
    print(f"  spurious_risk={baseline_check.spurious_risk}")
    print(f"  adjusted_confidence={baseline_check.adjusted_confidence:.4f}")
    print("  issues=")
    _print_list(baseline_check.issues)
    print("  required_verifications=")
    _print_list(baseline_check.required_verifications)
    print("Enhanced AntiSpurious:")
    print(f"  spurious_risk={enhanced_check.spurious_risk}")
    print(f"  adjusted_confidence={enhanced_check.adjusted_confidence:.4f}")
    print("  issues=")
    _print_list(enhanced_check.issues)
    print("  required_verifications=")
    _print_list(enhanced_check.required_verifications)
    print()
    print("Enhanced EventCard history_validation_summary:")
    print(enhanced_card.history_validation_summary)
    print()
    print(RISK_DISCLAIMER)


def _print_list(values: list[str]) -> None:
    if not values:
        print("  - none")
        return
    for value in values:
        print(f"  - {value}")


def main() -> None:
    """Run the Phase 5D.1 demo CLI."""
    parser = ArgumentParser(description="Run EventCard/AntiSpurious with history validation.")
    parser.add_argument("--demo-current-ai-export", action="store_true", help="Use the rich AI export-control context.")
    parser.add_argument(
        "--mock-outcome-scenario",
        choices=["aligned", "mixed", "opposite"],
        default="aligned",
        help="Deterministic mock current outcome scenario.",
    )
    parser.add_argument("--store-path", default=str(DEFAULT_HISTORICAL_CASE_STORE_PATH), help="Historical case JSON path.")
    args = parser.parse_args()

    result = run_event_with_history_validation_demo(
        demo_current_ai_export=args.demo_current_ai_export,
        mock_outcome_scenario=args.mock_outcome_scenario,
        store_path=args.store_path,
    )
    _print_result(result)


if __name__ == "__main__":
    main()
