"""Run the Phase 5B historical analogy demo."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.history import (  # noqa: E402
    DEFAULT_HISTORICAL_CASE_STORE_PATH,
    HistoricalAnalogyExplainer,
    HistoricalAnalogyRetriever,
    HistoricalCaseStore,
    build_demo_current_ai_export_context,
    build_seed_historical_cases,
    retrieve_analogies_for_tracked_event,
)
from eventalpha.news import DEFAULT_LIFECYCLE_STORE_PATH, EventLifecycleStore  # noqa: E402
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402


def run_historical_analogy_demo(
    query: str | None = None,
    event_type: str | None = None,
    assets: list[str] | None = None,
    entities: list[str] | None = None,
    industries: list[str] | None = None,
    tags: list[str] | None = None,
    region: str | None = None,
    causal_chain: list[str] | None = None,
    limit: int = 5,
    store_path: str | Path = DEFAULT_HISTORICAL_CASE_STORE_PATH,
    demo_current_ai_export: bool = False,
    from_active_event: int | None = None,
    lifecycle_store_path: str | Path = DEFAULT_LIFECYCLE_STORE_PATH,
) -> dict[str, Any]:
    """Load cases and retrieve historical analogies."""
    store = HistoricalCaseStore(store_path).load()
    cases = store.list_cases() if store.list_cases() else build_seed_historical_cases()
    retriever = HistoricalAnalogyRetriever(cases)
    message = None
    selected_tracked_event = None

    if demo_current_ai_export:
        context = build_demo_current_ai_export_context()
        query = str(context["query"])
        event_type = str(context["event_type"])
        assets = list(context["assets"])
        entities = list(context["entities"])
        industries = list(context["industries"])
        tags = list(context["tags"])
        causal_chain = list(context["causal_chain"])
    if from_active_event is not None:
        lifecycle_store = EventLifecycleStore(lifecycle_store_path).load()
        active_events = lifecycle_store.list_active_events()
        active_index = from_active_event - 1
        if active_index < 0 or active_index >= len(active_events):
            message = "No active tracked events found. Run lifecycle tracker first or use --demo-current-ai-export."
            analogies = []
        else:
            selected_tracked_event = active_events[active_index]
            analogies = retrieve_analogies_for_tracked_event(selected_tracked_event, cases, limit=limit)
    else:
        analogies = retriever.retrieve(
            query=query,
            event_type=event_type,
            assets=assets,
            entities=entities,
            industries=industries,
            tags=tags,
            region=region,
            causal_chain=causal_chain,
            limit=limit,
        )
    if not any([query, event_type, assets, entities, industries, tags, region, causal_chain]) and from_active_event is None:
        analogies = retriever.retrieve(query="AI chip export control", limit=limit)
    report = HistoricalAnalogyExplainer().explain_many(analogies)
    return {
        "store": store,
        "used_seed_memory": not bool(store.list_cases()),
        "cases": cases,
        "analogies": analogies,
        "report": report,
        "message": message,
        "selected_tracked_event": selected_tracked_event,
    }


def _print_result(result: dict[str, Any]) -> None:
    print("EventAlpha-MVP Historical Analogy Demo")
    print(f"Available cases: {len(result['cases'])}")
    print(f"Analogies: {len(result['analogies'])}")
    if result["used_seed_memory"]:
        print("Store not populated; using in-memory MVP seed cases.")
    if result.get("message"):
        print(result["message"])
    if result["analogies"]:
        context = result["analogies"][0].input_context
        if context:
            if context.context_label == "query-only":
                print("Input context: query-only; analogy score may be conservative.")
            elif context.context_label == "multi-dimensional":
                print("Input context: multi-dimensional; analogy score is more meaningful.")
            else:
                print("Input context: partial; analogy score may still be conservative.")
    print()
    print(result["report"])


def main() -> None:
    """Run the historical analogy demo CLI."""
    parser = ArgumentParser(description="Retrieve and explain historical analogies for EventAlpha.")
    parser.add_argument("--query", default=None, help="Keyword query.")
    parser.add_argument("--event-type", default=None, help="Exact event type signal.")
    parser.add_argument("--asset", action="append", default=None, help="Affected asset keyword, repeatable.")
    parser.add_argument("--entity", action="append", default=None, help="Entity keyword, repeatable.")
    parser.add_argument("--industry", action="append", default=None, help="Industry keyword, repeatable.")
    parser.add_argument("--tag", action="append", default=None, help="Tag keyword, repeatable.")
    parser.add_argument("--region", default=None, help="Region signal.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum analogies to show.")
    parser.add_argument("--store-path", default=str(DEFAULT_HISTORICAL_CASE_STORE_PATH), help="Historical case JSON path.")
    parser.add_argument("--demo-current-ai-export", action="store_true", help="Use a richer AI export-control current-event context.")
    parser.add_argument("--from-active-event", type=int, default=None, help="Use the Nth active lifecycle event as current context, 1-based.")
    parser.add_argument(
        "--lifecycle-store-path",
        default=str(DEFAULT_LIFECYCLE_STORE_PATH),
        help="Lifecycle JSON path for --from-active-event.",
    )
    args = parser.parse_args()

    result = run_historical_analogy_demo(
        query=args.query,
        event_type=args.event_type,
        assets=args.asset,
        entities=args.entity,
        industries=args.industry,
        tags=args.tag,
        region=args.region,
        limit=args.limit,
        store_path=args.store_path,
        demo_current_ai_export=args.demo_current_ai_export,
        from_active_event=args.from_active_event,
        lifecycle_store_path=args.lifecycle_store_path,
    )
    _print_result(result)
    if RISK_DISCLAIMER not in result["report"]:
        print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
