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
    build_seed_historical_cases,
)
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402


def run_historical_analogy_demo(
    query: str | None = None,
    event_type: str | None = None,
    assets: list[str] | None = None,
    entities: list[str] | None = None,
    industries: list[str] | None = None,
    tags: list[str] | None = None,
    region: str | None = None,
    limit: int = 5,
    store_path: str | Path = DEFAULT_HISTORICAL_CASE_STORE_PATH,
) -> dict[str, Any]:
    """Load cases and retrieve historical analogies."""
    store = HistoricalCaseStore(store_path).load()
    cases = store.list_cases() if store.list_cases() else build_seed_historical_cases()
    retriever = HistoricalAnalogyRetriever(cases)
    analogies = retriever.retrieve(
        query=query,
        event_type=event_type,
        assets=assets,
        entities=entities,
        industries=industries,
        tags=tags,
        region=region,
        limit=limit,
    )
    if not any([query, event_type, assets, entities, industries, tags, region]):
        analogies = retriever.retrieve(query="AI chip export control", limit=limit)
    report = HistoricalAnalogyExplainer().explain_many(analogies)
    return {
        "store": store,
        "used_seed_memory": not bool(store.list_cases()),
        "cases": cases,
        "analogies": analogies,
        "report": report,
    }


def _print_result(result: dict[str, Any]) -> None:
    print("EventAlpha-MVP Historical Analogy Demo")
    print(f"Available cases: {len(result['cases'])}")
    print(f"Analogies: {len(result['analogies'])}")
    if result["used_seed_memory"]:
        print("Store not populated; using in-memory MVP seed cases.")
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
    )
    _print_result(result)
    if RISK_DISCLAIMER not in result["report"]:
        print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
