"""Evaluate LLM extraction against a hand-written gold set."""

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
from eventalpha.schemas import RISK_DISCLAIMER, RawNews, StructuredEvent
from eventalpha.services import AssetNormalizationService


QUALITY_THRESHOLDS = {
    "event_type_accuracy": 0.90,
    "status_accuracy": 0.75,
    "asset_hint_recall_avg": 0.65,
    "entity_recall_avg": 0.50,
}


def load_gold_cases(case: str | None = None) -> list[dict]:
    """Load hand-written extraction gold cases."""
    path = ROOT / "eventalpha" / "examples" / "extraction_gold_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    if case is None:
        return cases
    if case.isdigit():
        return [cases[int(case)]]
    matched = [item for item in cases if item["case_id"] == case]
    if not matched:
        raise ValueError(f"Gold case not found: {case}")
    return matched


def raw_news_from_case(case: dict) -> RawNews:
    """Convert a gold case into RawNews."""
    return RawNews(
        title=case["raw_title"],
        raw_text=case["raw_text"],
        source=case.get("source", "unknown"),
        source_type=case.get("source_type", "unknown"),
        publish_time=case["publish_time"],
    )


def build_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    calibrated: bool = True,
    trace_dir: str | Path | None = None,
) -> LLMExtractionAgent:
    """Build an LLM extraction agent for gold evaluation."""
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


def evaluate_gold_cases(cases: list[dict], agent: LLMExtractionAgent) -> dict:
    """Evaluate extraction outputs against gold labels."""
    normalizer = AssetNormalizationService()
    evaluated_cases = []
    for case in cases:
        raw_news = raw_news_from_case(case)
        event: StructuredEvent | None = None
        error: str | None = None
        warnings: list[str] = []
        try:
            event = agent.extract(raw_news)
            warnings = list(agent.warnings)
        except Exception as exc:
            error = str(exc)

        evaluated_cases.append(
            _evaluate_one_case(
                case=case,
                event=event,
                warnings=warnings,
                error=error,
                normalizer=normalizer,
            )
        )

    summary = summarize_gold_results(evaluated_cases)
    ready, blocking = evaluate_quality_gate(summary)
    summary["ready_for_phase3c"] = ready
    summary["blocking_issues"] = blocking
    return {
        "summary": summary,
        "cases": evaluated_cases,
        "risk_disclaimer": RISK_DISCLAIMER,
    }


def summarize_gold_results(cases: list[dict]) -> dict:
    """Aggregate gold evaluation metrics."""
    successful = [case for case in cases if case.get("llm")]
    total = len(cases)
    event_type_matches = sum(case["metrics"]["event_type_match"] for case in successful)
    status_matches = sum(case["metrics"]["status_match"] for case in successful)
    novelty_in_range = sum(case["metrics"]["novelty_in_range"] for case in successful)

    summary = {
        "total_cases": total,
        "event_type_accuracy": _ratio(event_type_matches, total),
        "status_accuracy": _ratio(status_matches, total),
        "entity_recall_avg": _avg(successful, "entity_recall"),
        "industry_overlap_avg": _avg(successful, "industry_overlap"),
        "asset_hint_recall_avg": _avg(successful, "asset_hint_recall"),
        "novelty_in_range_count": novelty_in_range,
        "suspicious_event_time_count": sum(
            case["metrics"]["suspicious_event_time"] for case in successful
        ),
        "unknown_asset_count": sum(case["metrics"]["unknown_asset_count"] for case in successful),
        "postprocess_warning_count": sum(len(case["postprocess_warnings"]) for case in successful),
        "failed_case_count": total - len(successful),
        "severe_downstream_regression_count": 0,
        "entity_recall_by_case": {
            case["case_id"]: case["metrics"]["entity_recall"] for case in successful
        },
        "industry_overlap_by_case": {
            case["case_id"]: case["metrics"]["industry_overlap"] for case in successful
        },
        "worst_entity_cases": _worst_cases(successful, "entity_recall"),
        "worst_industry_cases": _worst_cases(successful, "industry_overlap"),
    }
    return summary


def evaluate_quality_gate(summary: dict) -> tuple[bool, list[str]]:
    """Evaluate fixed Phase 3C readiness gates."""
    blocking: list[str] = []
    for key, threshold in QUALITY_THRESHOLDS.items():
        if summary[key] < threshold:
            blocking.append(f"{key} below threshold {threshold}: {summary[key]}")
    if summary["suspicious_event_time_count"] != 0:
        blocking.append("suspicious_event_time_count must be 0")
    if summary["failed_case_count"] != 0:
        blocking.append("failed_case_count must be 0")
    if summary["severe_downstream_regression_count"] != 0:
        blocking.append("severe_downstream_regression_count must be 0")
    return not blocking, blocking


def write_report(report: dict, output_dir: str | Path = ROOT / "reports") -> tuple[Path, Path]:
    """Write JSON and Markdown reports."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "llm_extraction_gold_eval.json"
    md_path = report_dir / "llm_extraction_gold_eval.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def _evaluate_one_case(
    case: dict,
    event: StructuredEvent | None,
    warnings: list[str],
    error: str | None,
    normalizer: AssetNormalizationService,
) -> dict:
    gold = case["gold"]
    metrics = _empty_metrics()
    if event:
        metrics = {
            "event_type_match": event.event_type == gold["event_type"],
            "status_match": event.status == gold["status"],
            "entity_recall": _recall(gold["entities"], event.entities),
            "industry_overlap": _overlap(gold["affected_industries"], event.affected_industries),
            "asset_hint_recall": _recall(gold["affected_assets_hint"], event.affected_assets_hint),
            "novelty_in_range": _novelty_in_range(event.novelty_score, gold["novelty_score_range"]),
            "suspicious_event_time": int(event.event_time is not None and gold["event_time"] is None),
            "unknown_asset_count": sum(
                1 for asset in event.affected_assets_hint if not normalizer.is_known_asset(asset)
            ),
        }
    return {
        "case_id": case["case_id"],
        "case_category": case.get("case_category"),
        "title": case["raw_title"],
        "gold": gold,
        "llm": event.model_dump(mode="json") if event else None,
        "metrics": metrics,
        "postprocess_warnings": warnings,
        "error": error,
    }


def _empty_metrics() -> dict:
    return {
        "event_type_match": False,
        "status_match": False,
        "entity_recall": 0.0,
        "industry_overlap": 0.0,
        "asset_hint_recall": 0.0,
        "novelty_in_range": False,
        "suspicious_event_time": 0,
        "unknown_asset_count": 0,
    }


def _ratio(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _avg(cases: list[dict], metric: str) -> float:
    return round(mean([case["metrics"][metric] for case in cases]) if cases else 0.0, 4)


def _worst_cases(cases: list[dict], metric: str, limit: int = 5) -> list[dict]:
    """Return the lowest-scoring cases for a metric."""
    ranked = sorted(cases, key=lambda case: case["metrics"][metric])
    return [
        {
            "case_id": case["case_id"],
            "title": case["title"],
            metric: case["metrics"][metric],
        }
        for case in ranked[:limit]
    ]


def _recall(gold_values: list[str], actual_values: list[str]) -> float:
    gold = {_norm(item) for item in gold_values if item}
    actual = {_norm(item) for item in actual_values if item}
    if not gold:
        return 1.0
    return round(len(gold & actual) / len(gold), 4)


def _overlap(left_values: list[str], right_values: list[str]) -> float:
    left = {_norm(item) for item in left_values if item}
    right = {_norm(item) for item in right_values if item}
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 4)


def _novelty_in_range(score: float, score_range: list[float]) -> bool:
    low, high = score_range
    return low <= score <= high


def _norm(value: str) -> str:
    return "".join(str(value).split()).casefold()


def _render_markdown_report(report: dict) -> str:
    lines = [
        "# LLM Extraction Gold Evaluation",
        "",
        "This report is an engineering quality check, not investment advice.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Worst Entity Recall Cases", ""])
    for item in report["summary"].get("worst_entity_cases", []):
        lines.append(
            f"- `{item['case_id']}`: {item['entity_recall']} - {item['title']}"
        )
    lines.extend(["", "## Worst Industry Overlap Cases", ""])
    for item in report["summary"].get("worst_industry_cases", []):
        lines.append(
            f"- `{item['case_id']}`: {item['industry_overlap']} - {item['title']}"
        )
    lines.extend(["", "## Cases", ""])
    for case in report["cases"]:
        lines.append(f"### {case['case_id']}: {case['title']}")
        if case["error"]:
            lines.append(f"- error: {case['error']}")
        else:
            for key, value in case["metrics"].items():
                lines.append(f"- `{key}`: {value}")
            lines.append(f"- warnings: {len(case['postprocess_warnings'])}")
        lines.append("")
    lines.extend(["## Disclaimer", "", report["risk_disclaimer"], ""])
    return "\n".join(lines)


def _print_report(report: dict) -> None:
    print("EventAlpha-MVP: LLM extraction gold evaluation")
    print("\n## Summary")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print("\n## Cases")
    for case in report["cases"]:
        print(f"{case['case_id']}: {case['title']}")
        if case["error"]:
            print(f"  error: {case['error']}")
        else:
            print(f"  event_type_match: {case['metrics']['event_type_match']}")
            print(f"  status_match: {case['metrics']['status_match']}")
            print(f"  entity_recall: {case['metrics']['entity_recall']}")
            print(f"  asset_hint_recall: {case['metrics']['asset_hint_recall']}")
    print(f"\n{RISK_DISCLAIMER}")


def main() -> None:
    """Run gold extraction evaluation."""
    parser = ArgumentParser(description="Evaluate LLM extraction against gold cases.")
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
        agent = build_agent(
            real_llm=args.real_llm,
            model=args.model,
            base_url=args.base_url,
            calibrated=args.calibrated,
        )
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return

    report = evaluate_gold_cases(load_gold_cases(args.case), agent)
    _print_report(report)
    if args.write_report:
        json_path, md_path = write_report(report)
        print(f"\nWrote report: {json_path}")
        print(f"Wrote report: {md_path}")


if __name__ == "__main__":
    main()
