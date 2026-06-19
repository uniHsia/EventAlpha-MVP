"""Run the event pipeline with optional LLM causal reasoning."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import (
    LLMCausalReasoningAgent,
    LLMExtractionAgent,
    RuleBasedCausalReasoningAgent,
)
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
from scripts.run_llm_event_pipeline import build_llm_extraction_agent, load_demo_news


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


def build_llm_causal_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    failure_mode: str = "strict",
    trace_dir: str | Path | None = None,
) -> LLMCausalReasoningAgent:
    """Build an LLMCausalReasoningAgent for scripts and tests."""
    client = (
        OpenAICompatibleLLMClient(model=model, base_url=base_url)
        if real_llm
        else MockLLMClient()
    )
    runner = StructuredRunner(
        client=client,
        trace_writer=LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter(),
    )
    return LLMCausalReasoningAgent(runner=runner, failure_mode=failure_mode)  # type: ignore[arg-type]


def run_llm_causal_pipeline(
    raw_news: RawNews,
    causal_agent: LLMCausalReasoningAgent,
    extraction_agent: LLMExtractionAgent | None = None,
    ledger_service: LedgerService | None = None,
    persist: bool = True,
):
    """Run full event pipeline with the provided LLM causal agent."""
    return run_event_pipeline(
        raw_news,
        ledger_service=ledger_service,
        persist=persist,
        extraction_agent=extraction_agent,
        causal_agent=causal_agent,
    )


def _print_rule_based_causal_comparison(result: dict) -> None:
    rule_chain = RuleBasedCausalReasoningAgent().build_chain(
        structured_event=result["structured_event"],
        verification=result["verification"],
        impact_score=result["impact_score"],
        extraction_warnings=result.get("extraction_warnings", []),
    )
    llm_chain = result["causal_chain"]
    print("\n## Rule-based vs LLM causal")
    print(f"chain_length: rule_based={len(rule_chain.logic)} llm={len(llm_chain.logic)}")
    print(f"direction: rule_based={rule_chain.direction} llm={llm_chain.direction}")
    print(f"confidence: rule_based={rule_chain.confidence} llm={llm_chain.confidence}")
    print(f"affected_assets: rule_based={rule_chain.affected_assets}")
    print(f"affected_assets: llm={llm_chain.affected_assets}")


def main() -> None:
    """Run the LLM causal pipeline demo."""
    parser = ArgumentParser(description="Run EventAlpha pipeline with LLM causal reasoning.")
    parser.add_argument("--real-llm", action="store_true", help="Use real OpenAI-compatible API.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument("--failure-mode", default="strict", choices=["strict", "fallback"])
    parser.add_argument("--case", type=int, default=0, help="Demo event index.")
    parser.add_argument("--use-llm-extraction", action="store_true")
    args = parser.parse_args()

    raw_news = load_demo_news(args.case)
    try:
        causal_agent = build_llm_causal_agent(
            real_llm=args.real_llm,
            model=args.model,
            base_url=args.base_url,
            failure_mode=args.failure_mode,
        )
        extraction_agent = (
            build_llm_extraction_agent(
                real_llm=args.real_llm,
                model=args.model,
                base_url=args.base_url,
                failure_mode=args.failure_mode,
            )
            if args.use_llm_extraction
            else None
        )
        result = run_llm_causal_pipeline(
            raw_news,
            causal_agent=causal_agent,
            extraction_agent=extraction_agent,
            ledger_service=LedgerService(),
        )
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return
    except Exception as exc:
        print(f"LLM causal pipeline failed: {exc}")
        print(RISK_DISCLAIMER)
        return

    print("EventAlpha-MVP Demo: LLM causal pipeline")
    print("\n## Raw News")
    print(raw_news.raw_text)
    _print_model("StructuredEvent", result["structured_event"])
    _print_model("Credibility", result["verification"])
    _print_model("Impact Score", result["impact_score"])
    _print_model("LLM Causal Chain", result["causal_chain"])
    _print_rule_based_causal_comparison(result)
    if result.get("causal_warnings"):
        _print_model("Causal Warnings", result["causal_warnings"])
    _print_model("Anti-Spurious Check", result["anti_spurious_check"])
    _print_model("Market Mapping", result["market_mapping"])
    _print_model("Event Card", result["event_card"])
    print(f"\nPrediction Ledger ID: {result['prediction_ledger_entry'].prediction_id}")
    print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
