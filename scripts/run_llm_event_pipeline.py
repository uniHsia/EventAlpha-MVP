"""Run the full event pipeline with optional LLM extraction."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

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
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RISK_DISCLAIMER, RawNews
from eventalpha.services import LedgerService


def _print_model(title: str, value) -> None:
    print(f"\n## {title}")
    print(json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2))


def _to_jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def load_demo_news(index: int = 0) -> RawNews:
    """Load one bundled demo event."""
    demo_path = ROOT / "eventalpha" / "examples" / "demo_events.json"
    data = json.loads(demo_path.read_text(encoding="utf-8"))
    return RawNews(**data[index])


def build_llm_extraction_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    failure_mode: str = "strict",
    trace_dir: str | Path | None = None,
) -> LLMExtractionAgent:
    """Build an LLMExtractionAgent for scripts and tests."""
    client = (
        OpenAICompatibleLLMClient(model=model, base_url=base_url)
        if real_llm
        else MockLLMClient()
    )
    trace_writer = LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter()
    runner = StructuredRunner(client=client, trace_writer=trace_writer)
    return LLMExtractionAgent(runner=runner, failure_mode=failure_mode)  # type: ignore[arg-type]


def run_llm_event_pipeline(
    raw_news: RawNews,
    extraction_agent: LLMExtractionAgent,
    ledger_service: LedgerService | None = None,
    persist: bool = True,
):
    """Run full event pipeline with the provided LLM extraction agent."""
    return run_event_pipeline(
        raw_news,
        ledger_service=ledger_service,
        persist=persist,
        extraction_agent=extraction_agent,
    )


def _print_rule_based_comparison(raw_news: RawNews, llm_event) -> None:
    rule_event = RuleBasedExtractionAgent().extract(raw_news)
    fields = [
        "event_type",
        "event_title",
        "entities",
        "affected_industries",
        "affected_assets_hint",
    ]
    print("\n## Rule-based vs LLM extraction")
    for field in fields:
        print(f"{field}:")
        print(f"  rule_based: {getattr(rule_event, field)}")
        print(f"  llm:        {getattr(llm_event, field)}")


def main() -> None:
    """Run the LLM extraction event pipeline demo."""
    parser = ArgumentParser(description="Run EventAlpha event pipeline with LLM extraction.")
    parser.add_argument("--real-llm", action="store_true", help="Use real OpenAI-compatible API.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument("--failure-mode", default="strict", choices=["strict", "fallback"])
    parser.add_argument("--case", type=int, default=0, help="Demo event index.")
    parser.add_argument("--compare-rule-based", action="store_true")
    args = parser.parse_args()

    raw_news = load_demo_news(args.case)
    try:
        agent = build_llm_extraction_agent(
            real_llm=args.real_llm,
            model=args.model,
            base_url=args.base_url,
            failure_mode=args.failure_mode,
        )
        result = run_llm_event_pipeline(raw_news, agent, ledger_service=LedgerService())
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return
    except Exception as exc:
        print(f"LLM event pipeline failed: {exc}")
        print(RISK_DISCLAIMER)
        return

    print("EventAlpha-MVP Demo: LLM extraction event pipeline")
    print("\n## Raw News")
    print(raw_news.raw_text)
    _print_model("LLM StructuredEvent", result["structured_event"])
    if args.compare_rule_based:
        _print_rule_based_comparison(raw_news, result["structured_event"])
    if result["extraction_warnings"]:
        _print_model("Extraction Warnings", result["extraction_warnings"])
    _print_model("Credibility", result["verification"])
    _print_model("Impact Score", result["impact_score"])
    _print_model("Causal Chain", result["causal_chain"])
    _print_model("Anti-Spurious Check", result["anti_spurious_check"])
    _print_model("Market Mapping", result["market_mapping"])
    _print_model("Event Card", result["event_card"])
    print(f"\nPrediction Ledger ID: {result['prediction_ledger_entry'].prediction_id}")
    print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()

