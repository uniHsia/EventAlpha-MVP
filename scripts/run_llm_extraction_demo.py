"""Run a structured LLM extraction demo without touching the ledger."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.llm import (
    LLMConfigurationError,
    MockLLMClient,
    OpenAICompatibleLLMClient,
    PromptTemplate,
    StructuredRunner,
)
from eventalpha.llm.schema_utils import pydantic_to_json_schema
from eventalpha.schemas import RISK_DISCLAIMER, RawNews, StructuredEvent


def run_llm_extraction(
    raw_news: RawNews,
    client,
    trace_dir: str | Path | None = None,
) -> StructuredEvent:
    """Extract a StructuredEvent with a structured LLM client."""
    from eventalpha.llm import LLMTraceWriter

    template = PromptTemplate.from_file("eventalpha/prompts/extraction_event.md")
    prompt = template.render(
        json_schema=json.dumps(pydantic_to_json_schema(StructuredEvent), ensure_ascii=False),
        raw_news_json=json.dumps(raw_news.model_dump(mode="json"), ensure_ascii=False, indent=2),
    )
    trace_writer = LLMTraceWriter(trace_dir=trace_dir) if trace_dir else LLMTraceWriter()
    runner = StructuredRunner(client=client, trace_writer=trace_writer)
    return runner.run(
        prompt=prompt,
        output_schema=StructuredEvent,
        system_prompt="You are a structured event extraction component. Return JSON only.",
        prompt_name="extraction_event",
    )


def _load_demo_news(index: int = 0) -> RawNews:
    demo_path = ROOT / "eventalpha" / "examples" / "demo_events.json"
    data = json.loads(demo_path.read_text(encoding="utf-8"))
    return RawNews(**data[index])


def main() -> None:
    """Run mock or real LLM extraction."""
    parser = ArgumentParser(description="Run EventAlpha structured LLM extraction demo.")
    parser.add_argument("--real-llm", action="store_true", help="Use real OpenAI-compatible API.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL.")
    parser.add_argument("--case", type=int, default=0, help="Demo event index.")
    args = parser.parse_args()

    raw_news = _load_demo_news(args.case)
    if args.real_llm:
        try:
            client = OpenAICompatibleLLMClient(model=args.model, base_url=args.base_url)
        except LLMConfigurationError as exc:
            print(f"LLM configuration error: {exc}")
            print(RISK_DISCLAIMER)
            return
    else:
        client = MockLLMClient()

    try:
        event = run_llm_extraction(raw_news, client)
    except Exception as exc:
        print(f"LLM extraction failed: {exc}")
        print(RISK_DISCLAIMER)
        return

    print("EventAlpha-MVP Demo: LLM structured extraction")
    print("\n## Raw News")
    print(raw_news.raw_text)
    print("\n## StructuredEvent")
    print(json.dumps(event.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()

