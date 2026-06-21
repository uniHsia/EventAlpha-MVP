"""Run the offline EventAlpha end-to-end demo flow."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.demo import run_full_demo as _run_full_demo  # noqa: E402
from eventalpha.demo.demo_runner import FullDemoSummary, STREAMLIT_DEMO_INSTRUCTION  # noqa: E402


def run_full_demo_cli(
    *,
    scenario_id: str = "ai_export_control",
    reset_demo_state: bool = False,
    write_summary: bool = False,
    use_default_state: bool = False,
) -> FullDemoSummary:
    """Run the demo from tests or CLI code."""
    return _run_full_demo(
        scenario_id=scenario_id,
        reset_state=reset_demo_state,
        write_summary=write_summary,
        use_default_state=use_default_state,
    )


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = ArgumentParser(description="Run EventAlpha's offline full demo flow.")
    parser.add_argument("--scenario", default="ai_export_control", help="Demo scenario id.")
    parser.add_argument("--reset-demo-state", action="store_true", help="Reset isolated data/demo and reports/demo before running.")
    parser.add_argument("--write-summary", action="store_true", help="Write full_demo_summary Markdown/JSON.")
    parser.add_argument("--open-instructions", action="store_true", help="Print Streamlit opening instructions.")
    parser.add_argument("--use-default-state", action="store_true", help="Opt in to default project state instead of isolated demo state.")
    args = parser.parse_args(argv)

    summary = run_full_demo_cli(
        scenario_id=args.scenario,
        reset_demo_state=args.reset_demo_state,
        write_summary=args.write_summary,
        use_default_state=args.use_default_state,
    )
    print(_format_summary(summary, include_open_instructions=args.open_instructions))


def _format_summary(summary: FullDemoSummary, *, include_open_instructions: bool = False) -> str:
    lines = [
        "EventAlpha Full Demo Completed",
        "",
        f"Scenario: {summary.scenario_id}",
        f"Isolated state: {summary.isolated_state}",
        "",
    ]
    for index, step in enumerate(summary.steps, start=1):
        lines.append(f"{index}. {step.step_name}: {step.status}")
        for key, value in step.counts.items():
            lines.append(f"   {key}: {value}")
        for path in step.output_paths:
            lines.append(f"   path: {path}")
        for warning in step.warnings[:3]:
            lines.append(f"   warning: {warning}")
        for error in step.errors[:3]:
            lines.append(f"   error: {error}")
        lines.append("")

    prediction = summary.prediction
    event_card = summary.event_card
    lines.extend(
        [
            "Demo Objects:",
            f"   Prediction: {prediction.get('prediction_id', 'n/a')}",
            f"   EventCard: {event_card.get('card_id', 'n/a')}",
            f"   ReviewResults: {summary.review_result_count}",
            f"   RuleUpdates: {summary.rule_update_count}",
        ]
    )
    if summary.briefing_paths:
        lines.extend(
            [
                "",
                "Daily Briefing:",
                f"   Markdown: {summary.briefing_paths.get('markdown', 'n/a')}",
                f"   JSON: {summary.briefing_paths.get('json', 'n/a')}",
            ]
        )
    if summary.demo_summary_paths:
        lines.extend(
            [
                "",
                "Full Demo Summary:",
                f"   Markdown: {summary.demo_summary_paths.get('markdown', 'n/a')}",
                f"   JSON: {summary.demo_summary_paths.get('json', 'n/a')}",
            ]
        )
    lines.extend(
        [
            "",
            "Next:",
            f"   {summary.streamlit_instruction or STREAMLIT_DEMO_INSTRUCTION}",
        ]
    )
    if include_open_instructions:
        lines.extend(
            [
                "",
                "Open instructions:",
                "   The command above starts the read-only Streamlit console in demo mode.",
                "   It reads data/demo and reports/demo only; it does not start the scheduler daemon.",
            ]
        )
    lines.extend(["", summary.risk_disclaimer])
    return "\n".join(lines).strip()


if __name__ == "__main__":
    main()
