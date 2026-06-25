"""Scout candidate news and cluster them into event candidates."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.llm import LLMConfigurationError  # noqa: E402
from eventalpha.news import (  # noqa: E402
    ClusterCredibilityService,
    ClusterVerificationService,
    NewsClusterer,
    NewsKeywordFilter,
    NewsFetchResult,
    NewsSourceRegistry,
    build_mock_registry,
    build_real_registry,
    deduplicate_news,
    event_cluster_to_raw_news,
    normalize_cluster_credibility,
)
from eventalpha.orchestration import run_event_pipeline  # noqa: E402
from eventalpha.news.schemas import (  # noqa: E402
    CredibilityEvidence,
    EventClusterRecord,
    RawNewsItemRecord,
    SourceCheckRun,
    SourceCredibilityState,
)
from eventalpha.schemas import RISK_DISCLAIMER  # noqa: E402
from eventalpha.schemas.base import new_id  # noqa: E402
from eventalpha.services import LedgerService  # noqa: E402
from scripts.run_llm_anti_spurious_pipeline import build_llm_anti_spurious_agent  # noqa: E402
from scripts.run_llm_causal_pipeline import build_llm_causal_agent  # noqa: E402
from scripts.run_llm_event_pipeline import build_llm_extraction_agent  # noqa: E402


def run_event_cluster_scout(
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
    with_credibility: bool = False,
    persist: bool = False,
    ledger_service: LedgerService | None = None,
) -> dict[str, Any]:
    """Fetch, filter, cluster, verify, and optionally analyze candidate events."""
    selected_registry = registry or (
        build_real_registry(rss_feeds=rss_feeds, source=source) if real_fetch else build_mock_registry()
    )
    source_run_id = new_id("SRCRUN")
    ledger = ledger_service or (LedgerService() if persist else None)
    per_provider_results = []
    if ledger is not None:
        for entry in getattr(selected_registry, "source_entries", []):
            ledger.save_news_source(entry)

    all_items = []
    all_errors = []
    for provider in selected_registry.providers:
        try:
            provider_result = provider.fetch(query=query, limit=limit)
            per_provider_results.append((provider, provider_result, None))
            all_items.extend(provider_result.items)
            all_errors.extend(provider_result.errors)
        except Exception as exc:
            per_provider_results.append((provider, None, exc))
            all_errors.append(f"{getattr(provider, 'name', provider.__class__.__name__)} failed: {exc}")

    if ledger is not None:
        _persist_source_fetches(
            ledger=ledger,
            source_run_id=source_run_id,
            provider_results=per_provider_results,
            query=query,
        )

    fetch_result = NewsFetchResult(
        source_name="news_registry",
        items=all_items,
        errors=all_errors,
    )
    dedup_result = deduplicate_news(fetch_result.items)
    dedup_keys = {_dedup_key(item) for item in dedup_result.items}
    if ledger is not None:
        _persist_raw_news_items(
            ledger=ledger,
            source_run_id=source_run_id,
            items=fetch_result.items,
            dedup_keys=dedup_keys,
            query=query,
        )
    filter_result = NewsKeywordFilter().filter_items(dedup_result.items)
    clusterer = NewsClusterer()
    verifier = ClusterVerificationService()
    clusters = [verifier.verify(cluster) for cluster in clusterer.cluster(filter_result.candidates)]
    credibility_reports = (
        {cluster.cluster_id: ClusterCredibilityService().evaluate(cluster) for cluster in clusters}
        if with_credibility
        else {}
    )
    normalized_credibility = {
        cluster.cluster_id: normalize_cluster_credibility(cluster, credibility_reports.get(cluster.cluster_id))
        for cluster in clusters
    }
    clusters = [
        cluster.model_copy(
            update={
                "verification_status": normalized_credibility[cluster.cluster_id].verification_status,
                "confidence": normalized_credibility[cluster.cluster_id].credibility_score,
                "independent_confirmation": normalized_credibility[cluster.cluster_id].independent_confirmation,
                "debug_reasons": [
                    *list(cluster.debug_reasons or []),
                    f"normalized_credibility={normalized_credibility[cluster.cluster_id].verification_status}",
                ],
            }
        )
        for cluster in clusters
    ]
    ranked_candidates = rank_event_candidates(clusters, credibility_reports)
    clusters = [candidate["cluster"] for candidate in ranked_candidates]
    if ledger is not None:
        _persist_clusters_and_credibility(
            ledger=ledger,
            source_run_id=source_run_id,
            clusters=clusters,
            credibility_reports=credibility_reports,
        )

    analyses: list[dict[str, Any]] = []
    eligible_candidates = [
        candidate
        for candidate in ranked_candidates
        if candidate["cluster"].cluster_type in {"single_news_event", "multi_source_event", "official_update_cluster"}
    ]
    for candidate in eligible_candidates[: max(analyze_top, 0)]:
        cluster = candidate["cluster"]
        raw_news = event_cluster_to_raw_news(cluster, credibility_reports.get(cluster.cluster_id))
        raw_news.metadata["source_run_id"] = source_run_id
        raw_news.metadata["candidate_priority"] = f"{candidate['candidate_priority']:.4f}"
        raw_news.metadata["candidate_priority_reasons"] = ",".join(candidate["candidate_priority_reasons"])
        result = run_event_pipeline(
            raw_news,
            ledger_service=ledger,
            persist=persist,
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
        if ledger is not None:
            _persist_event_evidence(
                ledger=ledger,
                source_run_id=source_run_id,
                cluster=cluster,
                pipeline_result=result,
                credibility_report=credibility_reports.get(cluster.cluster_id),
            )
        analyses.append(
            {
                "cluster": cluster,
                "raw_news": raw_news,
                "pipeline_result": result,
                "candidate_priority": candidate["candidate_priority"],
                "candidate_priority_reasons": candidate["candidate_priority_reasons"],
            }
        )

    return {
        "source_run_id": source_run_id,
        "fetch_result": fetch_result,
        "provider_results": per_provider_results,
        "dedup_result": dedup_result,
        "filter_result": filter_result,
        "clusters": clusters,
        "ranked_candidates": ranked_candidates,
        "credibility_reports": credibility_reports,
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


def _print_clusters(result: dict[str, Any]) -> None:
    fetch_result = result["fetch_result"]
    dedup_result = result["dedup_result"]
    filter_result = result["filter_result"]
    clusters = result["clusters"]
    credibility_reports = result.get("credibility_reports", {})

    print("EventAlpha-MVP Event Cluster Scout")
    print(f"Fetched items: {len(fetch_result.items)}")
    print(f"Deduped items: {dedup_result.after_count} (duplicates={dedup_result.duplicate_count})")
    print(f"Candidate news items: {filter_result.after_count}")
    print(f"Event clusters: {len(clusters)}")
    if fetch_result.errors:
        print("\n## Source Errors")
        for error in fetch_result.errors:
            print(f"- {error}")

    print("\n## Event Clusters")
    for index, cluster in enumerate(clusters, start=1):
        candidate = next((item for item in result.get("ranked_candidates", []) if item["cluster"].cluster_id == cluster.cluster_id), None)
        print(
            f"{index}. {cluster.canonical_title} "
            f"(sources={cluster.source_count}, unique_sources={cluster.unique_source_count}, "
            f"cluster_type={cluster.cluster_type}, status={cluster.verification_status}, "
            f"confidence={cluster.confidence:.2f})"
        )
        if candidate:
            print(
                f"   candidate_priority={candidate['candidate_priority']:.2f} "
                f"reasons={', '.join(candidate['candidate_priority_reasons'])}"
            )
        print(f"   keywords={', '.join(cluster.dominant_keywords) or 'none'}")
        if cluster.debug_reasons:
            print(f"   debug={'; '.join(cluster.debug_reasons)}")
        for item in cluster.items:
            print(f"   - {item.title} [{item.source}]")
            if item.url:
                print(f"     {item.url}")
        report = credibility_reports.get(cluster.cluster_id)
        if report:
            print(
                f"   credibility={report.credibility_status} "
                f"score={report.credibility_score:.2f} "
                f"consistency={report.consistency_status} "
                f"official={report.official_evidence_status}"
            )
            if report.risk_flags:
                print(f"   risk_flags={', '.join(report.risk_flags)}")


def _print_analyses(result: dict[str, Any]) -> None:
    analyses = result["analyses"]
    if not analyses:
        return
    print("\n## Event Pipeline Analysis")
    for index, analysis in enumerate(analyses, start=1):
        cluster = analysis["cluster"]
        pipeline_result = analysis["pipeline_result"]
        print(f"\n### Analysis {index}: {cluster.canonical_title}")
        print(json.dumps(_to_jsonable(pipeline_result["event_card"]), ensure_ascii=False, indent=2))


def main() -> None:
    """Run the event cluster scout CLI."""
    parser = ArgumentParser(description="Collect, cluster, and screen event candidates for EventAlpha.")
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
    parser.add_argument("--analyze-top", type=int, default=0, help="Analyze top N clusters with EventAlpha.")
    parser.add_argument("--with-credibility", action="store_true", help="Include cluster credibility reports.")
    parser.add_argument("--persist", action="store_true", help="Persist source/cluster/evidence records to SQLite.")
    parser.add_argument("--use-llm-extraction", action="store_true")
    parser.add_argument("--use-llm-causal", action="store_true")
    parser.add_argument("--use-llm-anti-spurious", action="store_true")
    parser.add_argument("--failure-mode", default="fallback", choices=["strict", "fallback"])
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL when real LLM is used.")
    parser.add_argument("--base-url", default=None, help="Override OPENAI_BASE_URL when real LLM is used.")
    args = parser.parse_args()

    try:
        result = run_event_cluster_scout(
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
            with_credibility=args.with_credibility,
            persist=args.persist,
        )
    except LLMConfigurationError as exc:
        print(f"LLM configuration error: {exc}")
        print(RISK_DISCLAIMER)
        return
    _print_clusters(result)
    _print_analyses(result)
    print(f"\n{RISK_DISCLAIMER}")


def _persist_source_fetches(
    *,
    ledger: LedgerService,
    source_run_id: str,
    provider_results: list[tuple[Any, NewsFetchResult | None, Exception | None]],
    query: str | None,
) -> None:
    for provider, result, error in provider_results:
        provider_name = str(getattr(provider, "name", provider.__class__.__name__))
        fetched_at = result.fetched_at if result else None
        item_count = len(result.items) if result else 0
        errors = list(result.errors or []) if result else []
        status = "failed" if error or errors else "ok"
        note = None
        if hasattr(provider, "feed_url"):
            note = f"feed_url={getattr(provider, 'feed_url')}"
        elif hasattr(provider, "api_url"):
            note = f"api_url={getattr(provider, 'api_url')}"
        ledger.save_source_check_run(
            SourceCheckRun(
                source_run_id=source_run_id,
                source_name=provider_name,
                query=query,
                status=status,
                fetched_at=fetched_at,
                item_count=item_count,
                error_text=str(error) if error else "; ".join(errors[:2]) if errors else None,
                raw_result_notes=note,
            )
        )


def _persist_raw_news_items(
    *,
    ledger: LedgerService,
    source_run_id: str,
    items: list[Any],
    dedup_keys: set[str],
    query: str | None,
) -> None:
    seen_dedup: set[str] = set()
    for item in items:
        key = _dedup_key(item)
        is_duplicate = key in seen_dedup
        seen_dedup.add(key)
        ledger.save_raw_news_item(
            RawNewsItemRecord(
                source_run_id=source_run_id,
                news_id=item.news_id,
                title=item.title,
                summary=item.summary,
                url=item.url,
                source=item.source,
                source_type=item.source_type,
                published_at=item.published_at,
                language=item.language,
                country=item.country,
                raw_text=item.raw_text,
                tags=list(item.tags or []),
                fetched_at=item.fetched_at,
                query=query,
                is_duplicate=is_duplicate,
            )
        )


def _persist_clusters_and_credibility(
    *,
    ledger: LedgerService,
    source_run_id: str,
    clusters: list[Any],
    credibility_reports: dict[str, Any],
) -> None:
    for cluster in clusters:
        ledger.save_event_cluster(
            EventClusterRecord(
                source_run_id=source_run_id,
                cluster_id=cluster.cluster_id,
                canonical_title=cluster.canonical_title,
                canonical_summary=cluster.canonical_summary,
                source_count=cluster.source_count,
                item_count=cluster.item_count,
                unique_source_count=cluster.unique_source_count,
                mainstream_source_count=cluster.mainstream_source_count,
                first_seen_at=cluster.first_seen_at,
                last_seen_at=cluster.last_seen_at,
                dominant_keywords=list(cluster.dominant_keywords or []),
                candidate_event_type=cluster.candidate_event_type,
                cluster_type=cluster.cluster_type,
                independent_confirmation=cluster.independent_confirmation,
                verification_status=cluster.verification_status,
                confidence=cluster.confidence,
                debug_reasons=list(cluster.debug_reasons or []),
            )
        )
        ledger.save_cluster_news_links(
            source_run_id=source_run_id,
            cluster_id=cluster.cluster_id,
            news_ids=[item.news_id for item in cluster.items],
        )
        report = credibility_reports.get(cluster.cluster_id)
        if report is None:
            continue
        for source in report.source_summary:
            ledger.save_source_credibility_state(
                SourceCredibilityState(
                    source_name=source.source_name,
                    source_type=source.source_type,
                    credibility_tier=source.credibility_tier,
                    historical_accuracy=None,
                    weight=_weight_from_tier(source.credibility_tier),
                    last_verified_at=cluster.last_seen_at or cluster.first_seen_at,
                    notes=source.rationale,
                )
            )
            ledger.save_credibility_evidence(
                CredibilityEvidence(
                    source_run_id=source_run_id,
                    cluster_id=cluster.cluster_id,
                    evidence_key=f"source::{source.source_name}",
                    source_name=source.source_name,
                    evidence_type="source_summary",
                    claim_text=f"Source classified as {source.credibility_tier}.",
                    supporting_item_ids=[item.news_id for item in cluster.items if item.source == source.source_name],
                    supporting_sources=[source.source_name],
                    consistency_status=report.consistency_status,
                    official_evidence_status=report.official_evidence_status,
                    risk_flags=list(report.risk_flags or []),
                    note_text=f"{source.rationale} | cluster_verification={cluster.verification_status} score={cluster.confidence:.2f}",
                )
            )
        for claim in report.claims:
            ledger.save_credibility_evidence(
                CredibilityEvidence(
                    source_run_id=source_run_id,
                    cluster_id=cluster.cluster_id,
                    evidence_key=claim.claim_id,
                    source_name="|".join(claim.supporting_sources[:3]) if claim.supporting_sources else None,
                    evidence_type=claim.claim_type,
                    claim_text=claim.claim_text,
                    supporting_item_ids=list(claim.supporting_item_ids or []),
                    supporting_sources=list(claim.supporting_sources or []),
                    consistency_status=report.consistency_status,
                    official_evidence_status=report.official_evidence_status,
                    risk_flags=list(report.risk_flags or []),
                    note_text=f"cluster_verification={cluster.verification_status}; score={cluster.confidence:.2f}; "
                    + ("; ".join(report.verification_notes[:2]) if report.verification_notes else ""),
                )
            )


def _persist_event_evidence(
    *,
    ledger: LedgerService,
    source_run_id: str,
    cluster: Any,
    pipeline_result: dict[str, Any],
    credibility_report: Any | None,
) -> None:
    event = pipeline_result.get("structured_event")
    verification = pipeline_result.get("verification")
    if event is None or verification is None:
        return
    for index, evidence in enumerate(list(verification.evidence or [])):
        ledger.save_credibility_evidence(
            CredibilityEvidence(
                source_run_id=source_run_id,
                cluster_id=cluster.cluster_id,
                event_id=event.event_id,
                evidence_key=f"event::{event.event_id}::{index}",
                source_name=evidence.get("source"),
                evidence_type=evidence.get("type") or "verification_evidence",
                claim_text=evidence.get("type") or "verification_evidence",
                supporting_item_ids=[item.news_id for item in cluster.items],
                supporting_sources=[item.source for item in cluster.items],
                consistency_status=getattr(credibility_report, "consistency_status", None),
                official_evidence_status=getattr(credibility_report, "official_evidence_status", None),
                risk_flags=list(verification.risk_flags or []),
                note_text=(
                    f"verification_status={verification.verification_status}; "
                    f"credibility_score={verification.credibility_score:.2f}; "
                    f"prediction_gate={pipeline_result.get('prediction_gate', {}).get('status')}"
                ),
            )
        )


def _weight_from_tier(tier: str) -> float:
    normalized = str(tier or "").casefold()
    if normalized == "high":
        return 0.8
    if normalized == "medium":
        return 0.6
    if normalized == "low":
        return 0.4
    return 0.5


def _dedup_key(item: Any) -> str:
    if getattr(item, "url", None):
        return "url:" + str(item.url).strip().rstrip("/").casefold()
    return "title:" + " ".join(str(item.title).strip().casefold().split())


MARKET_RELEVANT_EVENT_TYPES = {
    "ai_export_control",
    "geopolitical_conflict",
    "rate_policy",
    "trade_tariff",
    "earthquake_supply_chain",
}


def rank_event_candidates(
    clusters: list[Any],
    credibility_reports: dict[str, Any],
) -> list[dict[str, Any]]:
    """Rank cluster candidates by analysis priority instead of collection order."""
    ranked: list[dict[str, Any]] = []
    for cluster in clusters:
        report = credibility_reports.get(cluster.cluster_id)
        priority = 0.0
        reasons: list[str] = []
        official_status = getattr(report, "official_evidence_status", None)
        if official_status == "official_source_present":
            priority += 0.22
            reasons.append("official_source_present")
        if cluster.cluster_type in {"official_update_cluster", "multi_source_event"}:
            priority += 0.18
            reasons.append(cluster.cluster_type)
        if cluster.candidate_event_type in MARKET_RELEVANT_EVENT_TYPES:
            priority += 0.18
            reasons.append("market_relevant")
        priority += min(max(float(cluster.confidence or 0), 0.0), 1.0) * 0.2
        if _asset_mapping_available(cluster):
            priority += 0.12
            reasons.append("asset_mapping_available")
        if cluster.mainstream_source_count:
            priority += 0.05
            reasons.append("credible_source_base")
        if cluster.last_seen_at:
            priority += 0.03
            reasons.append("recent")
        if cluster.cluster_type in {"same_source_topic_cluster", "analysis_digest"}:
            priority -= 0.30
            reasons.append("observation_cluster_penalty")
        ranked.append(
            {
                "cluster": cluster,
                "candidate_priority": round(priority, 4),
                "candidate_priority_reasons": reasons,
            }
        )
    ranked.sort(
        key=lambda item: (
            item["candidate_priority"],
            item["cluster"].confidence,
            item["cluster"].unique_source_count,
            item["cluster"].last_seen_at,
        ),
        reverse=True,
    )
    return ranked


def _asset_mapping_available(cluster: Any) -> bool:
    text = f"{cluster.canonical_title} {cluster.canonical_summary or ''}".casefold()
    return (
        cluster.candidate_event_type in MARKET_RELEVANT_EVENT_TYPES
        or any(marker in text for marker in ("chip", "oil", "gold", "tariff", "yield", "gpu", "semiconductor", "能源"))
    )


if __name__ == "__main__":
    main()
