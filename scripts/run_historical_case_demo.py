"""Run the Phase 5A historical case store demo."""

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
    HistoricalCaseStore,
    build_seed_historical_cases,
    search_cases,
    summarize_search_results,
)
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402


def run_historical_case_demo(
    query: str | None = None,
    event_type: str | None = None,
    assets: list[str] | None = None,
    entities: list[str] | None = None,
    tags: list[str] | None = None,
    limit: int = 5,
    seed: bool = False,
    store_path: str | Path = DEFAULT_HISTORICAL_CASE_STORE_PATH,
) -> dict[str, Any]:
    """Load or seed historical cases, then run a simple search."""
    store = HistoricalCaseStore(store_path).load()
    seed_cases = build_seed_historical_cases()
    if seed:
        for historical_case in seed_cases:
            store.upsert(historical_case)
        store.save()

    cases = store.list_cases() if store.list_cases() else seed_cases
    matches = search_cases(
        cases,
        query=query,
        event_type=event_type,
        assets=assets,
        entities=entities,
        tags=tags,
        limit=limit,
    )
    if not any([query, event_type, assets, entities, tags]):
        matches = cases[:limit]
    report = summarize_search_results(matches)
    return {
        "store": store,
        "used_seed_memory": not bool(store.list_cases()),
        "cases": cases,
        "matches": matches,
        "report": report,
    }


def _print_result(result: dict[str, Any]) -> None:
    print("EventAlpha-MVP Historical Case Demo")
    print(f"Available cases: {len(result['cases'])}")
    print(f"Matched cases: {len(result['matches'])}")
    if result["used_seed_memory"]:
        print("Store not populated; using in-memory MVP seed cases.")
    print()
    print(result["report"])


def main() -> None:
    """Run the historical case demo CLI."""
    parser = ArgumentParser(description="Search illustrative historical cases for EventAlpha.")
    parser.add_argument("--seed", action="store_true", help="Write MVP seed cases to the JSON store.")
    parser.add_argument("--query", default=None, help="Keyword query.")
    parser.add_argument("--event-type", default=None, help="Exact event type filter.")
    parser.add_argument("--asset", action="append", default=None, help="Affected asset keyword, repeatable.")
    parser.add_argument("--entity", action="append", default=None, help="Entity keyword, repeatable.")
    parser.add_argument("--tag", action="append", default=None, help="Tag keyword, repeatable.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum matches to show.")
    parser.add_argument("--store-path", default=str(DEFAULT_HISTORICAL_CASE_STORE_PATH), help="Historical case JSON path.")
    args = parser.parse_args()

    result = run_historical_case_demo(
        query=args.query,
        event_type=args.event_type,
        assets=args.asset,
        entities=args.entity,
        tags=args.tag,
        limit=args.limit,
        seed=args.seed,
        store_path=args.store_path,
    )
    _print_result(result)
    if RISK_DISCLAIMER not in result["report"]:
        print(f"\n{RISK_DISCLAIMER}")


if __name__ == "__main__":
    main()
