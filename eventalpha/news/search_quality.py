"""Search and collection quality reporting for EventAlpha."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel, new_id, utc_now

from .cluster_verification import ClusterVerificationService
from .clustering import NewsClusterer
from .dedup import deduplicate_news
from .filters import NewsKeywordFilter
from .source_registry import NewsSourceRegistry, build_mock_registry, build_real_registry


class SearchQualityReport(EventAlphaModel):
    """A lightweight report describing one news search/scout run."""

    run_id: str = Field(default_factory=lambda: new_id("SEARCH_QUALITY"))
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    demo_mode: bool = False
    raw_news_count: int = 0
    after_dedup_count: int = 0
    cluster_count: int = 0
    event_card_count: int = 0
    high_priority_event_count: int = 0
    ledger_prediction_count: int = 0
    source_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    failure_sources: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def build_search_quality_report(
    *,
    registry: NewsSourceRegistry | None = None,
    real_fetch: bool = False,
    source: str = "all",
    rss_feeds: list[str] | None = None,
    query: str | None = None,
    limit: int = 10,
    demo_mode: bool = False,
    event_cards: list[dict[str, Any]] | None = None,
    ledger_rows: list[dict[str, Any]] | None = None,
) -> SearchQualityReport:
    """Build an offline-first search quality report."""
    selected_registry = registry or (
        build_real_registry(rss_feeds=rss_feeds, source=source) if real_fetch else build_mock_registry()
    )
    fetch_result = selected_registry.fetch_all(query=query, limit_per_source=limit)
    dedup_result = deduplicate_news(fetch_result.items)
    filter_result = NewsKeywordFilter().filter_items(dedup_result.items)
    verifier = ClusterVerificationService()
    clusters = [verifier.verify(cluster) for cluster in NewsClusterer().cluster(filter_result.candidates)]
    event_card_rows = list(event_cards or [])
    ledger = list(ledger_rows or [])
    notes = [
        "默认使用离线 mock/news registry；真实来源需显式 --real-fetch。",
        f"candidate_count: {filter_result.after_count}",
    ]
    if fetch_result.errors:
        notes.append("存在来源失败或查询为空，详见 failure_sources。")
    return SearchQualityReport(
        demo_mode=demo_mode,
        raw_news_count=len(fetch_result.items),
        after_dedup_count=dedup_result.after_count,
        cluster_count=len(clusters),
        event_card_count=len(event_card_rows),
        high_priority_event_count=_count_high_priority(event_card_rows),
        ledger_prediction_count=len({row.get("prediction_id") or row.get("PredictionID") for row in ledger if row}),
        source_breakdown=_source_breakdown(fetch_result.items),
        failure_sources=_failure_sources(fetch_result.errors),
        notes=notes,
    )


def write_search_quality_report(
    report: SearchQualityReport,
    *,
    reports_dir: str | Path = "reports",
    report_date: date | None = None,
) -> dict[str, str]:
    """Write JSON and Markdown search quality reports."""
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    stamp = (report_date or date.today()).strftime("%Y%m%d")
    json_path = reports_path / f"search_quality_{stamp}.json"
    md_path = reports_path / f"search_quality_{stamp}.md"
    json_path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_search_quality_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_search_quality_markdown(report: SearchQualityReport) -> str:
    """Render the report as Markdown."""
    lines = [
        "# EventAlpha 搜索质量评估",
        "",
        f"- run_id: {report.run_id}",
        f"- generated_at: {report.generated_at}",
        f"- demo_mode: {str(report.demo_mode).lower()}",
        f"- raw_news_count: {report.raw_news_count}",
        f"- after_dedup_count: {report.after_dedup_count}",
        f"- cluster_count: {report.cluster_count}",
        f"- event_card_count: {report.event_card_count}",
        f"- high_priority_event_count: {report.high_priority_event_count}",
        f"- ledger_prediction_count: {report.ledger_prediction_count}",
        "",
        "## Source Breakdown",
        "",
        "| Source | Type | Count |",
        "|---|---|---:|",
    ]
    for row in report.source_breakdown:
        lines.append(f"| {_md(row.get('source'))} | {_md(row.get('source_type'))} | {row.get('count', 0)} |")
    lines.extend(["", "## Failure Sources", ""])
    if report.failure_sources:
        for row in report.failure_sources:
            lines.append(f"- {_md(row.get('source'))}: {_md(row.get('error'))}")
    else:
        lines.append("- 暂无")
    if report.notes:
        lines.extend(["", "## Notes", *[f"- {_md(note)}" for note in report.notes]])
    return "\n".join(lines).strip() + "\n"


def _source_breakdown(items: list[Any]) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str]] = Counter()
    for item in items:
        counter[(str(item.source or "unknown"), str(item.source_type or "unknown"))] += 1
    return [
        {"source": source, "source_type": source_type, "count": count}
        for (source, source_type), count in sorted(counter.items(), key=lambda pair: (-pair[1], pair[0][0]))
    ]


def _failure_sources(errors: list[str]) -> list[dict[str, str]]:
    results = []
    for error in errors:
        source = str(error).split(" ", 1)[0] if error else "unknown"
        results.append({"source": source, "error": str(error)})
    return results


def _count_high_priority(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if str(row.get("event_level") or row.get("事件等级") or "") in {"S", "A", "高"})


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
