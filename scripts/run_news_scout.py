"""Scout candidate news from mock, GDELT, or RSS sources."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.news import (  # noqa: E402
    NewsKeywordFilter,
    NewsSourceRegistry,
    build_mock_registry,
    build_real_registry,
    deduplicate_news,
    news_item_to_raw_news,
)
from eventalpha.llm import LLMConfigurationError  # noqa: E402
from eventalpha.orchestration import run_event_pipeline  # noqa: E402
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402
from scripts.run_llm_anti_spurious_pipeline import build_llm_anti_spurious_agent  # noqa: E402
from scripts.run_llm_causal_pipeline import build_llm_causal_agent  # noqa: E402
from scripts.run_llm_event_pipeline import build_llm_extraction_agent  # noqa: E402


def run_news_scout(
    query: str | None = None,
    limit: int = 10,
    real_fetch: bool = False,
    source: str = "all",
    rss_feeds: list[str] | None = None,
    analyze_top: int = 0,
    use_llm_extraction: bool = False,
    use_llm_causal: bool = False,
    use_llm_anti_spurious: bool = False,
    failure_mode: str = "fallback",
    model: str | None = None,
    base_url: str | None = None,
    registry: NewsSourceRegistry | None = None,
) -> dict[str, Any]:
    """Run the news scout flow and optionally analyze top candidates."""
    selected_registry = registry or (
        build_real_registry(rss_feeds=rss_feeds, source=source) if real_fetch else build_mock_registry()
    )
    fetch_result = selected_registry.fetch_all(query=query, limit_per_source=limit)
    dedup_result = deduplicate_news(fetch_result.items)
    filter_result = NewsKeywordFilter().filter_items(dedup_result.items)

    analyses: list[dict[str, Any]] = []
    for item in filter_result.candidates[: max(analyze_top, 0)]:
        raw_news = news_item_to_raw_news(item)
        result = run_event_pipeline(
            raw_news,
            persist=False,
            extraction_agent=(
                build_llm_extraction_agent(
                    real_llm=real_fetch,
                    model=model,
                    base_url=base_url,
                    failure_mode=failure_mode,
                )
                if use_llm_extraction
                else None
            ),
            causal_agent=(
                build_llm_causal_agent(
                    real_llm=real_fetch,
                    model=model,
                    base_url=base_url,
                    failure_mode=failure_mode,
                )
                if use_llm_causal
                else None
            ),
            anti_spurious_agent=(
                build_llm_anti_spurious_agent(
                    real_llm=real_fetch,
                    model=model,
                    base_url=base_url,
                    failure_mode=failure_mode,
                )
                if use_llm_anti_spurious
                else None
            ),
        )
        analyses.append({"news_item": item, "raw_news": raw_news, "pipeline_result": result})

    return {
        "fetch_result": fetch_result,
        "dedup_result": dedup_result,
        "filter_result": filter_result,
        "analyses": analyses,
    }


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "__dict__"):
        return _to_jsonable(vars(value))
    return value


def _print_candidates(result: dict[str, Any]) -> None:
    fetch_result = result["fetch_result"]
    dedup_result = result["dedup_result"]
    filter_result = result["filter_result"]

    print("EventAlpha-MVP News Scout")
    print(f"Fetched items: {len(fetch_result.items)}")
    print(f"Deduped items: {dedup_result.after_count} (duplicates={dedup_result.duplicate_count})")
    print(f"Candidate items: {filter_result.after_count}")
    if fetch_result.errors:
        print("\n## Source Errors")
        for error in fetch_result.errors:
            print(f"- {error}")

    print("\n## Candidate News")
    for index, item in enumerate(filter_result.candidates, start=1):
        reasons = ", ".join(filter_result.reasons.get(item.news_id, [])) or "unknown"
        print(f"{index}. [{reasons}] {item.title}")
        print(f"   source={item.source} id={item.news_id}")
        if item.url:
            print(f"   url={item.url}")


def _print_analyses(result: dict[str, Any]) -> None:
    analyses = result["analyses"]
    if not analyses:
        return

    print("\n## Event Pipeline Analysis")
    for index, analysis in enumerate(analyses, start=1):
        news_item = analysis["news_item"]
        pipeline_result = analysis["pipeline_result"]
        print(f"\n### Analysis {index}: {news_item.title}")
        print(json.dumps(_to_jsonable(pipeline_result["event_card"]), ensure_ascii=False, indent=2))


def main() -> None:
    """Run the news scout CLI."""
    parser = ArgumentParser(description="Collect and screen candidate news for EventAlpha.")
    parser.add_argument("--query", default=None, help="Optional provider query.")
    parser.add_argument("--limit", type=int, default=10, help="Limit per source.")
    parser.add_argument("--real-fetch", action="store_true", help="Enable real GDELT/RSS network fetch.")
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "gdelt", "rss"],
        help="Real-fetch source selection. Use rss to skip GDELT rate limits.",
    )
    parser.add_argument("--rss-feed", action="append", default=None, help="RSS feed URL, repeatable.")
    parser.add_argument("--analyze-top", type=int, default=0, help="Analyze top N candidates with EventAlpha.")
    parser.add_argument("--use-llm-extraction", action="store_true")
    parser.add_argument("--use-llm-causal", action="store_true")
    parser.add_argument("--use-llm-anti-spurious", action="store_true")
    parser.add_argument("--failure-mode", default="fallback", choices=["strict", "fallback"])
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL when real LLM is used.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL when real LLM is used.")
    args = parser.parse_args()

    try:
        result = run_news_scout(
            query=args.query,
            limit=args.limit,
            real_fetch=args.real_fetch,
            source=args.source,
            rss_feeds=args.rss_feed,
            analyze_top=args.analyze_top,
            use_llm_extraction=args.use_llm_extraction,
            use_llm_causal=args.use_llm_causal,
            use_llm_anti_spurious=args.use_llm_anti_spurious,
            failure_mode=args.failure_mode,
            model=args.model,
            base_url=args.base_url,
        )
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return
    _print_candidates(result)
    _print_analyses(result)
    print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
