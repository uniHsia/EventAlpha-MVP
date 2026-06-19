"""Evaluate LLM extraction against the rule-based extractor."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import LLMExtractionAgent, RuleBasedExtractionAgent
from eventalpha.llm import (
    LLMConfigurationError,
    LLMTraceWriter,
    MockLLMClient,
    OpenAICompatibleLLMClient,
    StructuredRunner,
)
from eventalpha.schemas import RISK_DISCLAIMER, RawNews, StructuredEvent
from eventalpha.services import AssetNormalizationService


COMPARE_FIELDS = [
    "event_type",
    "event_title",
    "status",
    "entities",
    "affected_industries",
    "affected_assets_hint",
    "event_time",
    "novelty_score",
]


def load_demo_news(case_index: int | None = None) -> list[RawNews]:
    """Load bundled demo news cases."""
    demo_path = ROOT / "eventalpha" / "examples" / "demo_events.json"
    payload = json.loads(demo_path.read_text(encoding="utf-8"))
    if case_index is not None:
        payload = [payload[case_index]]
    return [RawNews(**item) for item in payload]


def build_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    failure_mode: str = "strict",
    trace_dir: str | Path | None = None,
) -> LLMExtractionAgent:
    """Build an extraction agent for evaluation."""
    client = (
        OpenAICompatibleLLMClient(model=model, base_url=base_url)
        if real_llm
        else MockLLMClient()
    )
    runner = StructuredRunner(
        client=client,
        trace_writer=LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter(),
    )
    return LLMExtractionAgent(runner=runner, failure_mode=failure_mode)  # type: ignore[arg-type]


def evaluate_cases(
    raw_news_items: list[RawNews],
    agent: LLMExtractionAgent,
) -> dict:
    """Evaluate LLM extraction output for a list of RawNews cases."""
    rule_agent = RuleBasedExtractionAgent()
    normalizer = AssetNormalizationService()
    cases: list[dict] = []

    for index, raw_news in enumerate(raw_news_items):
        rule_event = rule_agent.extract(raw_news)
        llm_event: StructuredEvent | None = None
        error: str | None = None
        warnings: list[str] = []

        try:
            llm_event = agent.extract(raw_news)
            warnings = list(agent.warnings)
        except Exception as exc:  # Keep evaluation moving across cases.
            error = str(exc)

        cases.append(
            _evaluate_one_case(
                index=index,
                raw_news=raw_news,
                rule_event=rule_event,
                llm_event=llm_event,
                warnings=warnings,
                error=error,
                normalizer=normalizer,
            )
        )

    return {
        "summary": summarize_cases(cases),
        "cases": cases,
        "risk_disclaimer": RISK_DISCLAIMER,
    }


def summarize_cases(cases: list[dict]) -> dict:
    """Build aggregate extraction quality metrics."""
    successful = [case for case in cases if case.get("llm")]
    return {
        "total_cases": len(cases),
        "event_type_match_count": sum(
            1 for case in successful if case["diff"]["event_type_match"]
        ),
        "status_match_count": sum(
            1 for case in successful if case["diff"]["status_match"]
        ),
        "asset_hint_overlap_avg": round(
            mean([case["diff"]["asset_hint_overlap"] for case in successful]) if successful else 0.0,
            4,
        ),
        "entity_overlap_avg": round(
            mean([case["diff"]["entity_overlap"] for case in successful]) if successful else 0.0,
            4,
        ),
        "llm_unknown_asset_count": sum(
            case["diff"]["llm_unknown_asset_count"] for case in successful
        ),
        "event_time_suspicious_count": sum(
            1
            for case in successful
            if any("event_time" in warning for warning in case["postprocess_warnings"])
        ),
        "postprocess_warning_count": sum(
            len(case["postprocess_warnings"]) for case in successful
        ),
        "failed_case_count": len(cases) - len(successful),
    }


def write_report(report: dict, output_dir: str | Path = ROOT / "reports") -> tuple[Path, Path]:
    """Write JSON and Markdown evaluation reports."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "llm_extraction_eval.json"
    md_path = report_dir / "llm_extraction_eval.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def _evaluate_one_case(
    index: int,
    raw_news: RawNews,
    rule_event: StructuredEvent,
    llm_event: StructuredEvent | None,
    warnings: list[str],
    error: str | None,
    normalizer: AssetNormalizationService,
) -> dict:
    llm_payload = llm_event.model_dump(mode="json") if llm_event else None
    diff = _empty_diff()
    if llm_event:
        diff = {
            "event_type_match": rule_event.event_type == llm_event.event_type,
            "status_match": rule_event.status == llm_event.status,
            "asset_hint_overlap": _overlap(
                rule_event.affected_assets_hint,
                llm_event.affected_assets_hint,
            ),
            "entity_overlap": _overlap(rule_event.entities, llm_event.entities),
            "llm_unknown_asset_count": _unknown_asset_count(
                llm_event.affected_assets_hint,
                normalizer,
            ),
            "field_differences": {
                field: {
                    "rule_based": _field_value(rule_event, field),
                    "llm": _field_value(llm_event, field),
                }
                for field in COMPARE_FIELDS
                if _field_value(rule_event, field) != _field_value(llm_event, field)
            },
        }

    return {
        "case_index": index,
        "title": raw_news.title,
        "rule_based": rule_event.model_dump(mode="json"),
        "llm": llm_payload,
        "diff": diff,
        "postprocess_warnings": warnings,
        "error": error,
    }


def _empty_diff() -> dict:
    return {
        "event_type_match": False,
        "status_match": False,
        "asset_hint_overlap": 0.0,
        "entity_overlap": 0.0,
        "llm_unknown_asset_count": 0,
        "field_differences": {},
    }


def _field_value(event: StructuredEvent, field: str):
    value = getattr(event, field)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _overlap(left: list[str], right: list[str]) -> float:
    left_keys = {_norm(item) for item in left if item}
    right_keys = {_norm(item) for item in right if item}
    if not left_keys and not right_keys:
        return 1.0
    if not left_keys or not right_keys:
        return 0.0
    return round(len(left_keys & right_keys) / len(left_keys | right_keys), 4)


def _unknown_asset_count(assets: list[str], normalizer: AssetNormalizationService) -> int:
    return sum(1 for asset in assets if not normalizer.is_known_asset(asset))


def _norm(value: str) -> str:
    return "".join(str(value).split()).casefold()


def _render_markdown_report(report: dict) -> str:
    lines = [
        "# LLM Extraction Evaluation",
        "",
        "This report is an engineering quality check, not an investment recommendation.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Cases", ""])
    for case in report["cases"]:
        lines.append(f"### Case {case['case_index']}: {case['title']}")
        if case["error"]:
            lines.append(f"- error: {case['error']}")
        else:
            lines.append(f"- event_type_match: {case['diff']['event_type_match']}")
            lines.append(f"- status_match: {case['diff']['status_match']}")
            lines.append(f"- asset_hint_overlap: {case['diff']['asset_hint_overlap']}")
            lines.append(f"- entity_overlap: {case['diff']['entity_overlap']}")
            lines.append(f"- warnings: {len(case['postprocess_warnings'])}")
        lines.append("")
    lines.extend(["## Disclaimer", "", report["risk_disclaimer"], ""])
    return "\n".join(lines)


def _print_report(report: dict) -> None:
    print("EventAlpha-MVP: LLM extraction evaluation")
    print("\n## Summary")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print("\n## Cases")
    for case in report["cases"]:
        print(f"case {case['case_index']}: {case['title']}")
        if case["error"]:
            print(f"  error: {case['error']}")
            continue
        print(f"  event_type_match: {case['diff']['event_type_match']}")
        print(f"  status_match: {case['diff']['status_match']}")
        print(f"  asset_hint_overlap: {case['diff']['asset_hint_overlap']}")
        print(f"  entity_overlap: {case['diff']['entity_overlap']}")
        if case["postprocess_warnings"]:
            print("  warnings:")
            for warning in case["postprocess_warnings"]:
                print(f"    - {warning}")
    print(f"\n{RISK_DISCLAIMER}")


def main() -> None:
    """Run extraction evaluation from the command line."""
    parser = ArgumentParser(description="Evaluate LLM extraction against rule-based extraction.")
    parser.add_argument("--real-llm", action="store_true", help="Use real OpenAI-compatible API.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument("--case", type=int, default=None, help="Evaluate one demo case index.")
    parser.add_argument("--failure-mode", default="strict", choices=["strict", "fallback"])
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    try:
        agent = build_agent(
            real_llm=args.real_llm,
            model=args.model,
            base_url=args.base_url,
            failure_mode=args.failure_mode,
        )
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return

    report = evaluate_cases(load_demo_news(args.case), agent)
    _print_report(report)
    if args.write_report:
        json_path, md_path = write_report(report)
        print(f"\nWrote report: {json_path}")
        print(f"Wrote report: {md_path}")


if __name__ == "__main__":
    main()

