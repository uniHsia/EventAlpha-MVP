"""Run the event pipeline with optional LLM anti-spurious critic."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents import (
    LLMAntiSpuriousAgent,
    LLMExtractionAgent,
    LLMCausalReasoningAgent,
    RuleBasedAntiSpuriousAgent,
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
from scripts.run_llm_causal_pipeline import build_llm_causal_agent
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


def build_llm_anti_spurious_agent(
    real_llm: bool = False,
    model: str | None = None,
    base_url: str | None = None,
    failure_mode: str = "strict",
    trace_dir: str | Path | None = None,
) -> LLMAntiSpuriousAgent:
    """Build an LLMAntiSpuriousAgent for scripts and tests."""
    client = (
        OpenAICompatibleLLMClient(model=model, base_url=base_url)
        if real_llm
        else MockLLMClient()
    )
    runner = StructuredRunner(
        client=client,
        trace_writer=LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter(),
    )
    return LLMAntiSpuriousAgent(runner=runner, failure_mode=failure_mode)  # type: ignore[arg-type]


def run_llm_anti_spurious_pipeline(
    raw_news: RawNews,
    anti_spurious_agent: LLMAntiSpuriousAgent,
    extraction_agent: LLMExtractionAgent | None = None,
    causal_agent: LLMCausalReasoningAgent | None = None,
    ledger_service: LedgerService | None = None,
    persist: bool = True,
):
    """Run full event pipeline with the provided LLM anti-spurious agent."""
    return run_event_pipeline(
        raw_news,
        ledger_service=ledger_service,
        persist=persist,
        extraction_agent=extraction_agent,
        causal_agent=causal_agent,
        anti_spurious_agent=anti_spurious_agent,
    )


def _print_rule_based_comparison(result: dict) -> None:
    rule_check = RuleBasedAntiSpuriousAgent().check(
        structured_event=result["structured_event"],
        causal_chain=result["causal_chain"],
        verification=result["verification"],
        impact_score=result["impact_score"],
        extraction_warnings=result.get("extraction_warnings", []),
        causal_warnings=result.get("causal_warnings", []),
    )
    llm_check = result["anti_spurious_check"]
    print("\n## Rule-based vs LLM anti-spurious")
    print(f"spurious_risk: rule_based={rule_check.spurious_risk} llm={llm_check.spurious_risk}")
    print(
        "adjusted_confidence: "
        f"rule_based={rule_check.adjusted_confidence} llm={llm_check.adjusted_confidence}"
    )
    print(f"issues: rule_based={len(rule_check.issues)} llm={len(llm_check.issues)}")
    print(
        "required_verifications: "
        f"rule_based={len(rule_check.required_verifications)} "
        f"llm={len(llm_check.required_verifications)}"
    )


def main() -> None:
    """Run the LLM anti-spurious pipeline demo."""
    parser = ArgumentParser(description="Run EventAlpha pipeline with LLM anti-spurious critic.")
    parser.add_argument("--real-llm", action="store_true", help="Use real OpenAI-compatible API.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument("--failure-mode", default="strict", choices=["strict", "fallback"])
    parser.add_argument("--case", type=int, default=0, help="Demo event index.")
    parser.add_argument("--use-llm-extraction", action="store_true")
    parser.add_argument("--use-llm-causal", action="store_true")
    args = parser.parse_args()

    raw_news = load_demo_news(args.case)
    try:
        anti_spurious_agent = build_llm_anti_spurious_agent(
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
        causal_agent = (
            build_llm_causal_agent(
                real_llm=args.real_llm,
                model=args.model,
                base_url=args.base_url,
                failure_mode=args.failure_mode,
            )
            if args.use_llm_causal
            else None
        )
        result = run_llm_anti_spurious_pipeline(
            raw_news,
            anti_spurious_agent=anti_spurious_agent,
            extraction_agent=extraction_agent,
            causal_agent=causal_agent,
            ledger_service=LedgerService(),
        )
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return
    except Exception as exc:
        print(f"LLM anti-spurious pipeline failed: {exc}")
        print(RISK_DISCLAIMER)
        return

    print("EventAlpha-MVP Demo: LLM anti-spurious pipeline")
    print("\n## Raw News")
    print(raw_news.raw_text)
    _print_model("StructuredEvent", result["structured_event"])
    _print_model("Credibility", result["verification"])
    _print_model("Impact Score", result["impact_score"])
    _print_model("Causal Chain", result["causal_chain"])
    _print_model("LLM Anti-Spurious Check", result["anti_spurious_check"])
    _print_rule_based_comparison(result)
    if result.get("anti_spurious_warnings"):
        _print_model("Anti-Spurious Warnings", result["anti_spurious_warnings"])
    _print_model("Market Mapping", result["market_mapping"])
    _print_model("Event Card", result["event_card"])
    print(f"\nPrediction Ledger ID: {result['prediction_ledger_entry'].prediction_id}")
    print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
