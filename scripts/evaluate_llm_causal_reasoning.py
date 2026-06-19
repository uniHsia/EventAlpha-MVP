"""Evaluate LLM causal reasoning against rule-based causal chains."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import LLMCausalReasoningAgent, RuleBasedCausalReasoningAgent
from eventalpha.llm import (
    LLMConfigurationError,
    LLMTraceWriter,
    MockLLMClient,
    OpenAICompatibleLLMClient,
    StructuredRunner,
)
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import CausalChain, RISK_DISCLAIMER
from scripts.evaluate_llm_extraction_gold import load_gold_cases, raw_news_from_case


QUALITY_THRESHOLDS = {
    "affected_assets_overlap_avg": 0.70,
    "unsupported_asset_count": 0,
    "failed_case_count": 0,
    "too_long_chain_count": 2,
    "low_confidence_for_rumor_count": 0,
}


def build_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    trace_dir: str | Path | None = None,
) -> LLMCausalReasoningAgent:
    """Build an LLM causal agent for evaluation."""
    client = (
        OpenAICompatibleLLMClient(model=model, base_url=base_url)
        if real_llm
        else MockLLMClient()
    )
    runner = StructuredRunner(
        client=client,
        trace_writer=LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter(),
    )
    return LLMCausalReasoningAgent(runner=runner, failure_mode="fallback")


def evaluate_causal_cases(cases: list[dict], agent: LLMCausalReasoningAgent) -> dict:
    """Evaluate LLM causal reasoning over gold cases."""
    evaluated_cases = []
    for case in cases:
        raw_news = raw_news_from_case(case)
        base_result = run_event_pipeline(raw_news, persist=False)
        rule_chain = RuleBasedCausalReasoningAgent().build_chain(
            structured_event=base_result["structured_event"],
            verification=base_result["verification"],
            impact_score=base_result["impact_score"],
            extraction_warnings=base_result.get("extraction_warnings", []),
        )
        try:
            llm_chain = agent.build_chain(
                structured_event=base_result["structured_event"],
                verification=base_result["verification"],
                impact_score=base_result["impact_score"],
                supported_assets=base_result["structured_event"].affected_assets_hint,
                extraction_warnings=base_result.get("extraction_warnings", []),
            )
            error = None
            warnings = list(agent.warnings)
        except Exception as exc:
            llm_chain = None
            error = str(exc)
            warnings = list(agent.warnings)
        evaluated_cases.append(
            _evaluate_one_case(
                case=case,
                event_status=base_result["structured_event"].status,
                rule_chain=rule_chain,
                llm_chain=llm_chain,
                warnings=warnings,
                error=error,
            )
        )

    summary = summarize_causal_results(evaluated_cases)
    return {
        "summary": summary,
        "cases": evaluated_cases,
        "risk_disclaimer": RISK_DISCLAIMER,
    }


def summarize_causal_results(cases: list[dict]) -> dict:
    """Aggregate causal reasoning evaluation metrics."""
    successful = [case for case in cases if case.get("llm")]
    unsupported_count = sum(case["metrics"]["unsupported_asset_count"] for case in successful)
    too_long_count = sum(case["metrics"]["too_long_chain"] for case in successful)
    low_confidence_rumor_count = sum(
        case["metrics"]["low_confidence_for_rumor_violation"] for case in successful
    )
    summary = {
        "total_cases": len(cases),
        "affected_assets_overlap_avg": _avg(successful, "affected_assets_overlap"),
        "variable_type_coverage_avg": _avg(successful, "variable_type_coverage"),
        "direction_match_count": sum(case["metrics"]["direction_match"] for case in successful),
        "confidence_delta_avg": _avg(successful, "confidence_delta"),
        "unsupported_asset_count": unsupported_count,
        "too_long_chain_count": too_long_count,
        "low_confidence_for_rumor_count": low_confidence_rumor_count,
        "causal_warning_count": sum(len(case["causal_warnings"]) for case in successful),
        "failed_case_count": len(cases) - len(successful),
    }
    ready, blocking = evaluate_quality_gate(summary)
    summary["passes_quality_gate"] = ready
    summary["blocking_issues"] = blocking
    return summary


def evaluate_quality_gate(summary: dict) -> tuple[bool, list[str]]:
    """Evaluate fixed Phase 3C causal quality gates."""
    blocking: list[str] = []
    if summary["affected_assets_overlap_avg"] < QUALITY_THRESHOLDS["affected_assets_overlap_avg"]:
        blocking.append(
            "affected_assets_overlap_avg below threshold "
            f"{QUALITY_THRESHOLDS['affected_assets_overlap_avg']}: "
            f"{summary['affected_assets_overlap_avg']}"
        )
    if summary["unsupported_asset_count"] != 0:
        blocking.append("unsupported_asset_count must be 0")
    if summary["failed_case_count"] != 0:
        blocking.append("failed_case_count must be 0")
    if summary["too_long_chain_count"] > QUALITY_THRESHOLDS["too_long_chain_count"]:
        blocking.append("too_long_chain_count above threshold")
    if summary["low_confidence_for_rumor_count"] != 0:
        blocking.append("low_confidence_for_rumor_count must be 0")
    return not blocking, blocking


def write_report(report: dict, output_dir: str | Path = ROOT / "reports") -> tuple[Path, Path]:
    """Write JSON and Markdown reports."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "llm_causal_eval.json"
    md_path = report_dir / "llm_causal_eval.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def _evaluate_one_case(
    case: dict,
    event_status: str,
    rule_chain: CausalChain,
    llm_chain: CausalChain | None,
    warnings: list[str],
    error: str | None,
) -> dict:
    metrics = _empty_metrics()
    if llm_chain:
        metrics = {
            "chain_length": len(llm_chain.logic),
            "variable_type_coverage": _variable_type_coverage(llm_chain),
            "affected_assets_overlap": _overlap(rule_chain.affected_assets, llm_chain.affected_assets),
            "direction_match": rule_chain.direction == llm_chain.direction,
            "confidence_delta": round(abs(rule_chain.confidence - llm_chain.confidence), 4),
            "unsupported_asset_count": _unsupported_asset_count(warnings),
            "too_long_chain": len(llm_chain.logic) > 6,
            "low_confidence_for_rumor_violation": event_status == "rumor" and llm_chain.confidence > 0.55,
        }
    return {
        "case_id": case["case_id"],
        "title": case["raw_title"],
        "event_status": event_status,
        "rule_based": rule_chain.model_dump(mode="json"),
        "llm": llm_chain.model_dump(mode="json") if llm_chain else None,
        "causal_warnings": warnings,
        "error": error,
        "metrics": metrics,
    }


def _empty_metrics() -> dict:
    return {
        "chain_length": 0,
        "variable_type_coverage": 0.0,
        "affected_assets_overlap": 0.0,
        "direction_match": False,
        "confidence_delta": 0.0,
        "unsupported_asset_count": 0,
        "too_long_chain": False,
        "low_confidence_for_rumor_violation": False,
    }


def _variable_type_coverage(chain: CausalChain) -> float:
    if not chain.logic:
        return 0.0
    covered = sum(1 for step in chain.logic if step.variable_type)
    return round(covered / len(chain.logic), 4)


def _unsupported_asset_count(warnings: list[str]) -> int:
    """Count assets in unsupported-asset warning lines."""
    total = 0
    prefix = "Filtered unsupported causal affected_assets:"
    for warning in warnings:
        if prefix in warning:
            raw_assets = warning.split(prefix, 1)[1]
            total += len([item for item in raw_assets.split(",") if item.strip()])
    return total


def _avg(cases: list[dict], metric: str) -> float:
    return round(mean([case["metrics"][metric] for case in cases]) if cases else 0.0, 4)


def _overlap(left_values: list[str], right_values: list[str]) -> float:
    left = {_norm(item) for item in left_values if item}
    right = {_norm(item) for item in right_values if item}
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 4)


def _norm(value: str) -> str:
    return "".join(str(value).split()).casefold()


def _render_markdown_report(report: dict) -> str:
    lines = [
        "# LLM Causal Reasoning Evaluation",
        "",
        "This report is an engineering quality check, not investment advice.",
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
        if case["causal_warnings"]:
            lines.append(f"- warnings: {len(case['causal_warnings'])}")
        lines.append("")
    lines.extend(["## Disclaimer", "", report["risk_disclaimer"], ""])
    return "\n".join(lines)


def _print_report(report: dict) -> None:
    print("EventAlpha-MVP: LLM causal reasoning evaluation")
    print("\n## Summary")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print("\n## Cases")
    for case in report["cases"]:
        print(f"{case['case_id']}: {case['title']}")
        if case["error"]:
            print(f"  error: {case['error']}")
        print(f"  affected_assets_overlap: {case['metrics']['affected_assets_overlap']}")
        print(f"  variable_type_coverage: {case['metrics']['variable_type_coverage']}")
        print(f"  direction_match: {case['metrics']['direction_match']}")
        print(f"  confidence_delta: {case['metrics']['confidence_delta']}")
    print(f"\n{RISK_DISCLAIMER}")


def main() -> None:
    """Run LLM causal reasoning evaluation."""
    parser = ArgumentParser(description="Evaluate LLM causal reasoning.")
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

    report = evaluate_causal_cases(load_gold_cases(args.case), agent)
    _print_report(report)
    if args.write_report:
        json_path, md_path = write_report(report)
        print(f"\nWrote report: {json_path}")
        print(f"Wrote report: {md_path}")


if __name__ == "__main__":
    main()
