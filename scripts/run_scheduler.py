"""Run EventAlpha scheduler jobs."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.scheduler import (  # noqa: E402
    DEFAULT_SCHEDULER_RUNS_PATH,
    DEFAULT_SCHEDULER_STATE_PATH,
    EventAlphaAPScheduler,
    SchedulerJobConfig,
    SchedulerRunRecord,
    SchedulerStateStore,
    run_registered_job,
)
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402
from eventalpha.services import LedgerService  # noqa: E402


SUPPORTED_JOBS = (
    "news_lifecycle_scan",
    "candidate_analysis",
    "scheduler_status",
    "urgent_event_scan",
    "review_due_scan",
    "auto_review_runner",
)


def run_scheduler_once(
    job_type: str,
    *,
    execute: bool = False,
    real_fetch: bool = False,
    source: str = "rss",
    rss_feed: str | None = None,
    query: str | None = None,
    limit: int = 10,
    top_n: int | None = None,
    persist: bool = False,
    use_llm_extraction: bool = False,
    use_llm_causal: bool = False,
    use_llm_anti_spurious: bool = False,
    max_review_tasks: int = 5,
    review_horizons: list[str] | None = None,
    market_provider: str = "mock",
    allow_partial_review: bool = True,
    ledger_path: str | Path | None = None,
    interval_minutes: int = 60,
    state_path: str | Path = DEFAULT_SCHEDULER_STATE_PATH,
    runs_path: str | Path = DEFAULT_SCHEDULER_RUNS_PATH,
) -> dict[str, Any]:
    """Run one scheduler job and return structured output for tests."""
    effective_limit = top_n if top_n is not None else limit
    config = SchedulerJobConfig(
        job_id=job_type,
        job_type=job_type,
        interval_minutes=interval_minutes,
        query=query,
        source=source,
        rss_feed=rss_feed,
        limit=effective_limit,
        real_fetch=real_fetch,
        use_llm_extraction=use_llm_extraction,
        use_llm_causal=use_llm_causal,
        use_llm_anti_spurious=use_llm_anti_spurious,
        max_review_tasks=max_review_tasks,
        review_horizons=review_horizons,
        market_provider=market_provider,
        allow_partial_review=allow_partial_review,
        persist=persist,
        dry_run=not execute,
    )
    store = SchedulerStateStore(state_path=state_path, runs_path=runs_path)
    _ensure_config(store, config)
    record = run_registered_job(
        config,
        store,
        **_agent_kwargs(config),
        **_review_kwargs(config, ledger_path),
    )
    return {
        "config": config,
        "record": record,
        "store": store,
    }


def build_default_configs(
    *,
    execute: bool = False,
    interval_minutes: int = 60,
    real_fetch: bool = False,
    source: str = "rss",
    rss_feed: str | None = None,
    query: str | None = None,
    limit: int = 10,
    persist: bool = False,
    use_llm_extraction: bool = False,
    use_llm_causal: bool = False,
    use_llm_anti_spurious: bool = False,
    max_review_tasks: int = 5,
    review_horizons: list[str] | None = None,
    market_provider: str = "mock",
    allow_partial_review: bool = True,
) -> list[SchedulerJobConfig]:
    """Build default scheduler configs for daemon mode."""
    return [
        SchedulerJobConfig(
            job_id="news_lifecycle_scan",
            job_type="news_lifecycle_scan",
            interval_minutes=interval_minutes,
            query=query,
            source=source,
            rss_feed=rss_feed,
            limit=limit,
            real_fetch=real_fetch,
            persist=False,
            dry_run=not execute,
        ),
        SchedulerJobConfig(
            job_id="urgent_event_scan",
            job_type="urgent_event_scan",
            interval_minutes=max(15, min(interval_minutes, 60)),
            limit=min(limit, 10),
            persist=False,
            dry_run=not execute,
        ),
        SchedulerJobConfig(
            job_id="review_due_scan",
            job_type="review_due_scan",
            interval_minutes=interval_minutes,
            max_review_tasks=max_review_tasks,
            review_horizons=review_horizons,
            market_provider=market_provider,
            allow_partial_review=allow_partial_review,
            dry_run=True,
        ),
        SchedulerJobConfig(
            job_id="auto_review_runner",
            job_type="auto_review_runner",
            interval_minutes=interval_minutes,
            max_review_tasks=max_review_tasks,
            review_horizons=review_horizons,
            market_provider=market_provider,
            allow_partial_review=allow_partial_review,
            dry_run=not execute,
        ),
        SchedulerJobConfig(
            job_id="candidate_analysis",
            job_type="candidate_analysis",
            interval_minutes=interval_minutes,
            limit=min(limit, 3),
            use_llm_extraction=use_llm_extraction,
            use_llm_causal=use_llm_causal,
            use_llm_anti_spurious=use_llm_anti_spurious,
            persist=persist,
            dry_run=not execute,
        ),
    ]


def _agent_kwargs(config: SchedulerJobConfig) -> dict[str, Any]:
    if config.job_type != "candidate_analysis" or config.dry_run:
        return {}
    kwargs: dict[str, Any] = {}
    if config.use_llm_extraction:
        from scripts.run_llm_event_pipeline import build_llm_extraction_agent

        kwargs["extraction_agent"] = build_llm_extraction_agent(real_llm=False, failure_mode="fallback")
    if config.use_llm_causal:
        from scripts.run_llm_causal_pipeline import build_llm_causal_agent

        kwargs["causal_agent"] = build_llm_causal_agent(real_llm=False, failure_mode="fallback")
    if config.use_llm_anti_spurious:
        from scripts.run_llm_anti_spurious_pipeline import build_llm_anti_spurious_agent

        kwargs["anti_spurious_agent"] = build_llm_anti_spurious_agent(real_llm=False, failure_mode="fallback")
    return kwargs


def _review_kwargs(config: SchedulerJobConfig, ledger_path: str | Path | None) -> dict[str, Any]:
    if config.job_type not in {"review_due_scan", "auto_review_runner"}:
        return {}
    return {"ledger_service": LedgerService(ledger_path)} if ledger_path else {}


def _ensure_config(store: SchedulerStateStore, config: SchedulerJobConfig) -> None:
    jobs = [job for job in store.load_config() if job.job_id != config.job_id]
    jobs.append(config)
    store.save_config(jobs)


def _print_record(record: SchedulerRunRecord) -> None:
    print("EventAlpha-MVP Scheduler")
    print(f"run_id={record.run_id}")
    print(f"job_id={record.job_id}")
    print(f"job_type={record.job_type}")
    print(f"status={record.status}")
    print(f"fetched_items={record.fetched_items}")
    print(f"candidate_items={record.candidate_items}")
    print(f"clusters_processed={record.clusters_processed}")
    print(f"lifecycle_updates={record.lifecycle_updates}")
    print(f"analyzed_events={record.analyzed_events}")
    if record.notes:
        print("notes=")
        for note in record.notes:
            print(f"  - {note}")
    if record.warnings:
        print("warnings=")
        for warning in record.warnings:
            print(f"  - {warning}")
    if record.errors:
        print("errors=")
        for error in record.errors:
            print(f"  - {error}")
    print(f"\n{RISK_DISCLAIMER}")


def _parse_review_horizons(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    horizons: list[str] = []
    for value in values:
        horizons.extend(item.strip() for item in value.split(",") if item.strip())
    return horizons or None


def main(argv: list[str] | None = None) -> None:
    """Run the scheduler CLI."""
    parser = ArgumentParser(description="Run EventAlpha scheduler jobs.")
    parser.add_argument("--once", choices=SUPPORTED_JOBS, help="Run one scheduler job once.")
    parser.add_argument("--status", action="store_true", help="Run scheduler_status once.")
    parser.add_argument("--daemon", action="store_true", help="Start APScheduler interval jobs.")
    parser.add_argument("--execute", action="store_true", help="Execute job actions instead of dry-run.")
    parser.add_argument("--real-fetch", action="store_true", help="Allow real network news fetch.")
    parser.add_argument("--source", default="rss", choices=["all", "gdelt", "rss"], help="Real-fetch source selection.")
    parser.add_argument("--rss-feed", default=None, help="RSS feed URL.")
    parser.add_argument("--query", default=None, help="Provider query.")
    parser.add_argument("--limit", type=int, default=10, help="Item or active event limit.")
    parser.add_argument("--top-n", type=int, default=None, help="Priority event display/analysis limit.")
    parser.add_argument("--persist", action="store_true", help="Allow candidate analysis to write ledger.")
    parser.add_argument("--max-review-tasks", type=int, default=5, help="Maximum due review tasks to scan or run.")
    parser.add_argument(
        "--review-horizon",
        action="append",
        default=None,
        help="Review horizon filter; repeat or pass comma-separated values such as T+1,T+3.",
    )
    parser.add_argument(
        "--market-provider",
        default="mock",
        choices=["mock", "csv", "router", "akshare"],
        help="Market provider for auto_review_runner execute mode.",
    )
    parser.add_argument("--allow-partial-review", dest="allow_partial_review", action="store_true", default=True)
    parser.add_argument("--no-allow-partial-review", dest="allow_partial_review", action="store_false")
    parser.add_argument("--use-llm-extraction", action="store_true", help="Use mock/real LLM extraction when executing candidate analysis.")
    parser.add_argument("--use-llm-causal", action="store_true", help="Use mock/real LLM causal reasoning when executing candidate analysis.")
    parser.add_argument("--use-llm-anti-spurious", action="store_true", help="Use mock/real LLM anti-spurious check when executing candidate analysis.")
    parser.add_argument("--interval-minutes", type=int, default=60, help="Interval for daemon jobs.")
    parser.add_argument("--state-path", default=str(DEFAULT_SCHEDULER_STATE_PATH), help="Scheduler state JSON path.")
    parser.add_argument("--runs-path", default=str(DEFAULT_SCHEDULER_RUNS_PATH), help="Scheduler runs JSONL path.")
    parser.add_argument("--ledger-path", default=None, help="Optional SQLite ledger path for review jobs.")
    args = parser.parse_args(argv)

    if args.daemon:
        store = SchedulerStateStore(args.state_path, args.runs_path)
        daemon_limit = args.top_n if args.top_n is not None else args.limit
        configs = build_default_configs(
            execute=args.execute,
            interval_minutes=args.interval_minutes,
            real_fetch=args.real_fetch,
            source=args.source,
            rss_feed=args.rss_feed,
            query=args.query,
            limit=daemon_limit,
            persist=args.persist,
            use_llm_extraction=args.use_llm_extraction,
            use_llm_causal=args.use_llm_causal,
            use_llm_anti_spurious=args.use_llm_anti_spurious,
            max_review_tasks=args.max_review_tasks,
            review_horizons=_parse_review_horizons(args.review_horizon),
            market_provider=args.market_provider,
            allow_partial_review=args.allow_partial_review,
        )
        store.save_config(configs)
        runner = EventAlphaAPScheduler(configs, store=store)
        runner.start()
        print(f"Scheduler started with jobs: {', '.join(runner.list_registered_job_ids())}")
        print(f"dry_run={not args.execute} real_fetch={args.real_fetch} persist={args.persist}")
        print(RISK_DISCLAIMER)
        return

    job_type = "scheduler_status" if args.status else args.once
    if not job_type:
        job_type = "scheduler_status"
    result = run_scheduler_once(
        job_type,
        execute=args.execute,
        real_fetch=args.real_fetch,
        source=args.source,
        rss_feed=args.rss_feed,
        query=args.query,
        limit=args.limit,
        top_n=args.top_n,
        persist=args.persist,
        use_llm_extraction=args.use_llm_extraction,
        use_llm_causal=args.use_llm_causal,
        use_llm_anti_spurious=args.use_llm_anti_spurious,
        max_review_tasks=args.max_review_tasks,
        review_horizons=_parse_review_horizons(args.review_horizon),
        market_provider=args.market_provider,
        allow_partial_review=args.allow_partial_review,
        ledger_path=args.ledger_path,
        interval_minutes=args.interval_minutes,
        state_path=args.state_path,
        runs_path=args.runs_path,
    )
    _print_record(result["record"])


if __name__ == "__main__":
    main()
