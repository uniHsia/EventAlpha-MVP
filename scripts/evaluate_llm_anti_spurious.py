"""Evaluate LLM anti-spurious critic behavior."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import LLMAntiSpuriousAgent
from eventalpha.llm import (
    LLMConfigurationError,
    LLMTraceWriter,
    MockLLMClient,
    OpenAICompatibleLLMClient,
    StructuredRunner,
)
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import AntiSpuriousCheck, EventCard, RISK_DISCLAIMER
from scripts.evaluate_llm_extraction_gold import load_gold_cases, raw_news_from_case


QUALITY_THRESHOLDS = {
    "failed_case_count": 0,
    "overconfident_rumor_count": 0,
    "missing_required_verification_count": 0,
    "empty_critique_count": 2,
    "second_order_issue_detected_count": 1,
    "max_issue_count": 5,
    "max_required_verification_count": 5,
}


def build_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    trace_dir: str | Path | None = None,
) -> LLMAntiSpuriousAgent:
    """Build an LLM anti-spurious agent for evaluation."""
    client = (
        OpenAICompatibleLLMClient(model=model, base_url=base_url)
        if real_llm
        else MockLLMClient()
    )
    runner = StructuredRunner(
        client=client,
        trace_writer=LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter(),
    )
    return LLMAntiSpuriousAgent(runner=runner, failure_mode="fallback")


def evaluate_anti_spurious_cases(cases: list[dict], agent: LLMAntiSpuriousAgent) -> dict:
    """Evaluate LLM anti-spurious checks over gold cases."""
    evaluated_cases = []
    for case in cases:
        raw_news = raw_news_from_case(case)
        rule_result = run_event_pipeline(raw_news, persist=False)
        rule_check = rule_result["anti_spurious_check"]
        event_status = rule_result["structured_event"].status

        try:
            llm_result = run_event_pipeline(
                raw_news,
                persist=False,
                anti_spurious_agent=agent,
            )
            llm_check = llm_result["anti_spurious_check"]
            event_card = llm_result["event_card"]
            diagnostics = dict(agent.last_diagnostics)
            warnings = list(llm_result.get("anti_spurious_warnings", []))
            error = None
        except Exception as exc:
            llm_check = None
            event_card = None
            diagnostics = dict(agent.last_diagnostics)
            warnings = list(agent.warnings)
            error = str(exc)

        evaluated_cases.append(
            _evaluate_one_case(
                case=case,
                event_status=event_status,
                rule_check=rule_check,
                llm_check=llm_check,
                event_card=event_card,
                diagnostics=diagnostics,
                warnings=warnings,
                error=error,
            )
        )

    summary = summarize_anti_spurious_results(evaluated_cases)
    return {
        "summary": summary,
        "cases": evaluated_cases,
        "risk_disclaimer": RISK_DISCLAIMER,
    }


def summarize_anti_spurious_results(cases: list[dict]) -> dict:
    """Aggregate anti-spurious evaluation metrics."""
    successful = [case for case in cases if case.get("llm")]
    distribution = {"low": 0, "medium": 0, "high": 0}
    for case in successful:
        distribution[case["llm"]["spurious_risk"]] += 1

    summary = {
        "total_cases": len(cases),
        "spurious_risk_distribution": distribution,
        "low_risk_count": distribution["low"],
        "medium_risk_count": distribution["medium"],
        "high_risk_count": distribution["high"],
        "adjusted_confidence_delta_avg": _avg(successful, "adjusted_confidence_delta"),
        "required_verification_count_avg": _avg(successful, "required_verification_count"),
        "issue_count_avg": _avg(successful, "issue_count"),
        "issue_count_after_compression_avg": _avg(
            successful,
            "issue_count_after_compression",
        ),
        "required_verification_count_after_compression_avg": _avg(
            successful,
            "required_verification_count_after_compression",
        ),
        "max_issue_count": _max(successful, "issue_count_after_compression"),
        "max_required_verification_count": _max(
            successful,
            "required_verification_count_after_compression",
        ),
        "risk_calibration_count": sum(
            case["metrics"]["risk_calibration_applied"] for case in successful
        ),
        "event_card_risk_factor_count_avg": _avg(successful, "event_card_risk_factor_count"),
        "event_card_verification_indicator_count_avg": _avg(
            successful,
            "event_card_verification_indicator_count",
        ),
        "high_risk_for_rumor_count": sum(
            case["metrics"]["high_risk_for_rumor"] for case in successful
        ),
        "overconfident_rumor_count": sum(
            case["metrics"]["overconfident_rumor"] for case in successful
        ),
        "second_order_issue_detected_count": sum(
            case["metrics"]["second_order_issue_detected"] for case in successful
        ),
        "missing_required_verification_count": sum(
            case["metrics"]["missing_required_verification"] for case in successful
        ),
        "empty_critique_count": sum(case["metrics"]["empty_critique"] for case in successful),
        "failed_case_count": len(cases) - len(successful),
    }
    summary["soft_balance_notes"] = _evaluate_balance_notes(summary)
    ready, blocking = evaluate_quality_gate(summary)
    summary["passes_quality_gate"] = ready
    summary["blocking_issues"] = blocking
    return summary


def evaluate_quality_gate(summary: dict) -> tuple[bool, list[str]]:
    """Evaluate Phase 3D.5 anti-spurious quality gates."""
    blocking: list[str] = []
    if summary["failed_case_count"] != QUALITY_THRESHOLDS["failed_case_count"]:
        blocking.append("failed_case_count must be 0")
    if summary["overconfident_rumor_count"] != QUALITY_THRESHOLDS["overconfident_rumor_count"]:
        blocking.append("overconfident_rumor_count must be 0")
    if (
        summary["missing_required_verification_count"]
        != QUALITY_THRESHOLDS["missing_required_verification_count"]
    ):
        blocking.append("missing_required_verification_count must be 0")
    if summary["empty_critique_count"] > QUALITY_THRESHOLDS["empty_critique_count"]:
        blocking.append("empty_critique_count above threshold")
    if (
        summary["second_order_issue_detected_count"]
        < QUALITY_THRESHOLDS["second_order_issue_detected_count"]
    ):
        blocking.append("second_order_issue_detected_count below threshold")
    if summary["max_issue_count"] > QUALITY_THRESHOLDS["max_issue_count"]:
        blocking.append("max_issue_count above threshold")
    if (
        summary["max_required_verification_count"]
        > QUALITY_THRESHOLDS["max_required_verification_count"]
    ):
        blocking.append("max_required_verification_count above threshold")
    return not blocking, blocking


def write_report(report: dict, output_dir: str | Path = ROOT / "reports") -> tuple[Path, Path]:
    """Write JSON and Markdown reports."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "llm_anti_spurious_eval.json"
    md_path = report_dir / "llm_anti_spurious_eval.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def _evaluate_one_case(
    case: dict,
    event_status: str,
    rule_check: AntiSpuriousCheck,
    llm_check: AntiSpuriousCheck | None,
    event_card: EventCard | None,
    diagnostics: dict[str, int | str | bool],
    warnings: list[str],
    error: str | None,
) -> dict:
    metrics = _empty_metrics()
    if llm_check and event_card:
        text = " ".join(llm_check.issues + llm_check.required_verifications)
        metrics = {
            "adjusted_confidence_delta": round(
                abs(rule_check.adjusted_confidence - llm_check.adjusted_confidence),
                4,
            ),
            "required_verification_count": int(
                diagnostics.get(
                    "raw_required_verification_count",
                    len(llm_check.required_verifications),
                )
            ),
            "issue_count": int(diagnostics.get("raw_issue_count", len(llm_check.issues))),
            "required_verification_count_after_compression": len(
                llm_check.required_verifications
            ),
            "issue_count_after_compression": len(llm_check.issues),
            "risk_calibration_applied": bool(diagnostics.get("calibration_applied", False)),
            "high_risk_for_rumor": event_status == "rumor" and llm_check.spurious_risk == "high",
            "overconfident_rumor": event_status == "rumor" and llm_check.adjusted_confidence > 0.55,
            "second_order_issue_detected": _has_second_order_signal(text),
            "missing_required_verification": len(llm_check.required_verifications) == 0,
            "empty_critique": not llm_check.issues and not llm_check.required_verifications,
            "event_card_risk_factor_count": len(event_card.risk_factors),
            "event_card_verification_indicator_count": len(
                event_card.verification_indicators
            ),
        }
    return {
        "case_id": case["case_id"],
        "title": case["raw_title"],
        "event_status": event_status,
        "rule_based": rule_check.model_dump(mode="json"),
        "llm": llm_check.model_dump(mode="json") if llm_check else None,
        "event_card": event_card.model_dump(mode="json") if event_card else None,
        "anti_spurious_warnings": warnings,
        "diagnostics": diagnostics,
        "error": error,
        "metrics": metrics,
    }


def _empty_metrics() -> dict:
    return {
        "adjusted_confidence_delta": 0.0,
        "required_verification_count": 0,
        "issue_count": 0,
        "required_verification_count_after_compression": 0,
        "issue_count_after_compression": 0,
        "risk_calibration_applied": False,
        "high_risk_for_rumor": False,
        "overconfident_rumor": False,
        "second_order_issue_detected": False,
        "missing_required_verification": True,
        "empty_critique": True,
        "event_card_risk_factor_count": 0,
        "event_card_verification_indicator_count": 0,
    }


def _evaluate_balance_notes(summary: dict) -> list[str]:
    notes: list[str] = []
    if summary["low_risk_count"] == 0:
        notes.append(
            "No low-risk cases were produced. This usually means every case still carried "
            "severe critique concepts or warning floors."
        )
    if summary["high_risk_count"] > summary["total_cases"] / 2:
        notes.append(
            "High-risk cases cover a majority of the set. Review calibration thresholds or "
            "critic prompt severity before using the critic on live news flow."
        )
    return notes


def _has_second_order_signal(text: str) -> bool:
    compact = "".join(text.split()).casefold()
    keywords = [
        "secondorder",
        "second-order",
        "watch",
        "二阶",
        "二级",
        "间接",
        "watchasset",
    ]
    return any("".join(keyword.split()).casefold() in compact for keyword in keywords)


def _avg(cases: list[dict], metric: str) -> float:
    return round(mean([case["metrics"][metric] for case in cases]) if cases else 0.0, 4)


def _max(cases: list[dict], metric: str) -> int:
    return max((int(case["metrics"][metric]) for case in cases), default=0)


def _render_markdown_report(report: dict) -> str:
    lines = [
        "# LLM Anti-Spurious Evaluation",
        "",
        "This report checks the critic layer; it is not investment advice.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Cases", ""])
    for case in report["cases"]:
        lines.append(f"### {case['case_id']}: {case['title']}")
        if case["error"]:
            lines.append(f"- error: {case['error']}")
        for key, value in case["metrics"].items():
            lines.append(f"- `{key}`: {value}")
        if case["anti_spurious_warnings"]:
            lines.append(f"- warnings: {len(case['anti_spurious_warnings'])}")
        lines.append("")
    lines.extend(["## Disclaimer", "", report["risk_disclaimer"], ""])
    return "\n".join(lines)


def _print_report(report: dict) -> None:
    print("EventAlpha-MVP: LLM anti-spurious evaluation")
    print("\n## Summary")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print("\n## Cases")
    for case in report["cases"]:
        print(f"{case['case_id']}: {case['title']}")
        if case["error"]:
            print(f"  error: {case['error']}")
        print(f"  issue_count: {case['metrics']['issue_count']}")
        print(
            "  issue_count_after_compression: "
            f"{case['metrics']['issue_count_after_compression']}"
        )
        print(
            "  required_verification_count: "
            f"{case['metrics']['required_verification_count']}"
        )
        print(
            "  required_verification_count_after_compression: "
            f"{case['metrics']['required_verification_count_after_compression']}"
        )
        print(f"  risk_calibration_applied: {case['metrics']['risk_calibration_applied']}")
        print(f"  empty_critique: {case['metrics']['empty_critique']}")
        print(f"  overconfident_rumor: {case['metrics']['overconfident_rumor']}")
    print(f"\n{RISK_DISCLAIMER}")


def main() -> None:
    """Run LLM anti-spurious evaluation."""
    parser = ArgumentParser(description="Evaluate LLM anti-spurious critic.")
    parser.add_argument("--real-llm", action="store_true", help="Use real OpenAI-compatible API.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument("--case", default=None, help="Case index or case_id.")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    try:
        agent = build_agent(real_llm=args.real_llm, model=args.model, base_url=args.base_url)
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return

    report = evaluate_anti_spurious_cases(load_gold_cases(args.case), agent)
    _print_report(report)
    if args.write_report:
        json_path, md_path = write_report(report)
        print(f"\nWrote report: {json_path}")
        print(f"Wrote report: {md_path}")


if __name__ == "__main__":
    main()
