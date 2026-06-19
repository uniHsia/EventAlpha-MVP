"""Evaluate downstream consistency caused by extraction differences."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import (
    LLMConfigurationError,
    LLMTraceWriter,
    MockLLMClient,
    OpenAICompatibleLLMClient,
    StructuredRunner,
)
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RISK_DISCLAIMER, RawNews
from scripts.evaluate_llm_extraction_gold import load_gold_cases, raw_news_from_case


def build_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    calibrated: bool = True,
    trace_dir: str | Path | None = None,
) -> LLMExtractionAgent:
    """Build an LLM extraction agent for downstream evaluation."""
    client = (
        OpenAICompatibleLLMClient(model=model, base_url=base_url)
        if real_llm
        else MockLLMClient()
    )
    runner = StructuredRunner(
        client=client,
        trace_writer=LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter(),
    )
    return LLMExtractionAgent(runner=runner, enable_calibration=calibrated)


def evaluate_downstream_cases(
    cases: list[dict],
    llm_agent: LLMExtractionAgent,
    calibrated_agent: LLMExtractionAgent,
) -> dict:
    """Evaluate downstream outputs for rule, LLM, and calibrated LLM extraction."""
    evaluated_cases = []
    for case in cases:
        raw_news = raw_news_from_case(case)
        rule_result = run_event_pipeline(raw_news, persist=False)
        llm_result, llm_error = _safe_pipeline(raw_news, llm_agent)
        calibrated_result, calibrated_error = _safe_pipeline(raw_news, calibrated_agent)
        evaluated_cases.append(
            _evaluate_one_case(
                case=case,
                rule_result=rule_result,
                llm_result=llm_result,
                llm_error=llm_error,
                calibrated_result=calibrated_result,
                calibrated_error=calibrated_error,
            )
        )

    return {
        "summary": summarize_downstream_results(evaluated_cases),
        "cases": evaluated_cases,
        "risk_disclaimer": RISK_DISCLAIMER,
    }


def summarize_downstream_results(cases: list[dict]) -> dict:
    """Aggregate downstream consistency metrics for calibrated LLM outputs."""
    successful = [case for case in cases if case["calibrated_llm"]]
    return {
        "total_cases": len(cases),
        "event_level_changed_count": sum(
            case["metrics"]["event_level_changed"] for case in successful
        ),
        "trigger_alert_changed_count": sum(
            case["metrics"]["trigger_alert_changed"] for case in successful
        ),
        "missed_alert_count": sum(
            case["metrics"].get("missed_alert", False) for case in successful
        ),
        "over_alert_count": sum(
            case["metrics"].get("over_alert", False) for case in successful
        ),
        "gold_event_level_mismatch_count": sum(
            case["metrics"].get("gold_event_level_mismatch", False) for case in successful
        ),
        "gold_trigger_alert_mismatch_count": sum(
            case["metrics"].get("gold_trigger_alert_mismatch", False) for case in successful
        ),
        "mapped_asset_overlap_avg": round(
            mean([case["metrics"]["mapped_asset_overlap"] for case in successful])
            if successful
            else 0.0,
            4,
        ),
        "impact_score_delta_avg": round(
            mean([case["metrics"]["impact_score_delta"] for case in successful])
            if successful
            else 0.0,
            4,
        ),
        "severe_downstream_regression_count": sum(
            case["metrics"]["severe_downstream_regression"] for case in successful
        ),
        "failed_case_count": len(cases) - len(successful),
    }


def write_report(report: dict, output_dir: str | Path = ROOT / "reports") -> tuple[Path, Path]:
    """Write JSON and Markdown downstream reports."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "extraction_downstream_eval.json"
    md_path = report_dir / "extraction_downstream_eval.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def _safe_pipeline(raw_news: RawNews, extraction_agent: LLMExtractionAgent) -> tuple[dict | None, str | None]:
    try:
        return run_event_pipeline(raw_news, persist=False, extraction_agent=extraction_agent), None
    except Exception as exc:
        return None, str(exc)


def _evaluate_one_case(
    case: dict,
    rule_result: dict,
    llm_result: dict | None,
    llm_error: str | None,
    calibrated_result: dict | None,
    calibrated_error: str | None,
) -> dict:
    metrics = _empty_metrics()
    if calibrated_result:
        metrics = _compare_outputs(case, rule_result, calibrated_result)
    return {
        "case_id": case["case_id"],
        "case_category": case.get("case_category"),
        "title": case["raw_title"],
        "gold": case["gold"],
        "rule_based": _summarize_pipeline(rule_result),
        "llm": _summarize_pipeline(llm_result) if llm_result else None,
        "llm_error": llm_error,
        "calibrated_llm": _summarize_pipeline(calibrated_result) if calibrated_result else None,
        "calibrated_error": calibrated_error,
        "metrics": metrics,
    }


def _compare_outputs(case: dict, rule_result: dict, llm_result: dict) -> dict:
    rule_score = rule_result["impact_score"]
    llm_score = llm_result["impact_score"]
    rule_assets = _mapped_asset_names(rule_result)
    llm_assets = _mapped_asset_names(llm_result)
    overlap = _overlap(rule_assets, llm_assets)
    impact_delta = abs(llm_score.impact_score - rule_score.impact_score)
    gold = case["gold"]
    missed_alert = bool(gold["expected_trigger_alert"] and not llm_score.trigger_alert)
    over_alert = bool((not gold["expected_trigger_alert"]) and llm_score.trigger_alert)
    gold_event_level_mismatch = llm_score.event_level != gold["expected_event_level"]
    gold_trigger_alert_mismatch = llm_score.trigger_alert != gold["expected_trigger_alert"]
    severe = _is_severe_regression(
        case=case,
        rule_result=rule_result,
        llm_result=llm_result,
        mapped_asset_overlap=overlap,
        impact_score_delta=impact_delta,
    )
    return {
        "event_level_changed": rule_score.event_level != llm_score.event_level,
        "trigger_alert_changed": rule_score.trigger_alert != llm_score.trigger_alert,
        "missed_alert": missed_alert,
        "over_alert": over_alert,
        "gold_event_level_mismatch": gold_event_level_mismatch,
        "gold_trigger_alert_mismatch": gold_trigger_alert_mismatch,
        "mapped_asset_overlap": overlap,
        "impact_score_delta": impact_delta,
        "severe_downstream_regression": severe,
    }


def _is_severe_regression(
    case: dict,
    rule_result: dict,
    llm_result: dict,
    mapped_asset_overlap: float,
    impact_score_delta: int,
) -> bool:
    gold = case["gold"]
    llm_score = llm_result["impact_score"]
    if gold["expected_event_level"] in {"A", "S"} and llm_score.event_level in {"C", "D"}:
        return True
    if gold["expected_trigger_alert"] and not llm_score.trigger_alert:
        return True
    if mapped_asset_overlap < 0.5:
        return True
    if impact_score_delta > 15:
        return True
    return False


def _summarize_pipeline(result: dict) -> dict:
    score = result["impact_score"]
    prediction = result["prediction_ledger_entry"]
    return {
        "event_type": result["structured_event"].event_type,
        "status": result["structured_event"].status,
        "impact_score": score.impact_score,
        "event_level": score.event_level,
        "trigger_alert": score.trigger_alert,
        "tracking_mode": score.tracking_mode,
        "mapped_assets": _mapped_asset_names(result),
        "review_schedule": prediction.review_schedule,
        "extraction_warnings": result.get("extraction_warnings", []),
    }


def _mapped_asset_names(result: dict) -> list[str]:
    return [asset.asset_name for asset in result["market_mapping"].mapped_assets]


def _empty_metrics() -> dict:
    return {
        "event_level_changed": False,
        "trigger_alert_changed": False,
        "missed_alert": False,
        "over_alert": False,
        "gold_event_level_mismatch": False,
        "gold_trigger_alert_mismatch": False,
        "mapped_asset_overlap": 0.0,
        "impact_score_delta": 0,
        "severe_downstream_regression": True,
    }


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
        "# Extraction Downstream Evaluation",
        "",
        "This report checks whether extraction changes alter downstream research outputs.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Cases", ""])
    for case in report["cases"]:
        lines.append(f"### {case['case_id']}: {case['title']}")
        for key, value in case["metrics"].items():
            lines.append(f"- `{key}`: {value}")
        if case["calibrated_error"]:
            lines.append(f"- calibrated_error: {case['calibrated_error']}")
        lines.append("")
    lines.extend(["## Disclaimer", "", report["risk_disclaimer"], ""])
    return "\n".join(lines)


def _print_report(report: dict) -> None:
    print("EventAlpha-MVP: extraction downstream evaluation")
    print("\n## Summary")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print("\n## Cases")
    for case in report["cases"]:
        print(f"{case['case_id']}: {case['title']}")
        print(f"  event_level_changed: {case['metrics']['event_level_changed']}")
        print(f"  trigger_alert_changed: {case['metrics']['trigger_alert_changed']}")
        print(f"  missed_alert: {case['metrics'].get('missed_alert', False)}")
        print(f"  over_alert: {case['metrics'].get('over_alert', False)}")
        print(
            "  gold_event_level_mismatch: "
            f"{case['metrics'].get('gold_event_level_mismatch', False)}"
        )
        print(
            "  gold_trigger_alert_mismatch: "
            f"{case['metrics'].get('gold_trigger_alert_mismatch', False)}"
        )
        print(f"  mapped_asset_overlap: {case['metrics']['mapped_asset_overlap']}")
        print(f"  impact_score_delta: {case['metrics']['impact_score_delta']}")
        print(f"  severe_downstream_regression: {case['metrics']['severe_downstream_regression']}")
    print(f"\n{RISK_DISCLAIMER}")


def main() -> None:
    """Run downstream consistency evaluation."""
    parser = ArgumentParser(description="Evaluate downstream consistency of extraction outputs.")
    parser.add_argument("--real-llm", action="store_true", help="Use real OpenAI-compatible API.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument("--case", default=None, help="Case index or case_id.")
    parser.add_argument("--write-report", action="store_true")
    parser.set_defaults(calibrated=True)
    parser.add_argument("--calibrated", dest="calibrated", action="store_true")
    parser.add_argument("--no-calibrated", dest="calibrated", action="store_false")
    args = parser.parse_args()

    try:
        llm_agent = build_agent(
            real_llm=args.real_llm,
            model=args.model,
            base_url=args.base_url,
            calibrated=False,
        )
        calibrated_agent = build_agent(
            real_llm=args.real_llm,
            model=args.model,
            base_url=args.base_url,
            calibrated=args.calibrated,
        )
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return

    report = evaluate_downstream_cases(load_gold_cases(args.case), llm_agent, calibrated_agent)
    _print_report(report)
    if args.write_report:
        json_path, md_path = write_report(report)
        print(f"\nWrote report: {json_path}")
        print(f"Wrote report: {md_path}")


if __name__ == "__main__":
    main()
