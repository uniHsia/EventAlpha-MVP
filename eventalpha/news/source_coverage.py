"""Source coverage reporting for EventAlpha news discovery."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel, utc_now

from .gdelt_provider import GDELTProvider
from .rss_provider import RSSProvider
from .source_registry import NewsSourceRegistry, build_mock_registry, build_real_registry


class SourceCoverageItem(EventAlphaModel):
    """Status of one configured or planned information source."""

    source_name: str
    source_type: str
    enabled: bool = True
    status: str = "not_checked"
    last_checked_at: str | None = None
    last_item_count: int | None = None
    last_error: str | None = None
    notes: str | None = None


class SourceCoverageReport(EventAlphaModel):
    """A compact source coverage report."""

    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    demo_mode: bool = False
    enabled_count: int = 0
    ok_count: int = 0
    failed_count: int = 0
    placeholder_count: int = 0
    latest_checked_at: str | None = None
    items: list[SourceCoverageItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


PLACEHOLDER_SOURCES = (
    SourceCoverageItem(
        source_name="Official Sources",
        source_type="official",
        enabled=False,
        status="placeholder",
        notes="官方公告/API 聚合尚未接入；当前仅作为覆盖范围占位。",
    ),
    SourceCoverageItem(
        source_name="Financial Media",
        source_type="financial_media",
        enabled=False,
        status="placeholder",
        notes="专业财经媒体源尚未配置为稳定 provider。",
    ),
    SourceCoverageItem(
        source_name="Industry Sources",
        source_type="industry_source",
        enabled=False,
        status="placeholder",
        notes="行业协会/产业链来源尚未配置为稳定 provider。",
    ),
)


def collect_source_coverage(
    *,
    registry: NewsSourceRegistry | None = None,
    real_fetch: bool = False,
    source: str = "all",
    rss_feeds: list[str] | None = None,
    query: str | None = None,
    limit: int = 10,
    check_sources: bool = True,
    demo_mode: bool = False,
) -> SourceCoverageReport:
    """Collect source coverage without claiming placeholder sources are connected."""
    selected_registry = registry or (
        build_real_registry(rss_feeds=rss_feeds, source=source) if real_fetch else build_mock_registry()
    )
    items: list[SourceCoverageItem] = []
    notes = [
        "默认离线模式仅检查 Demo RawNews；真实 RSS/GDELT 需要显式 --real-fetch。",
    ]
    if real_fetch:
        notes = ["真实来源检查已显式启用；失败会记录为 failed，不回退伪造成功。"]

    for provider in selected_registry.providers:
        base = _provider_item(provider)
        if not check_sources:
            items.append(base)
            continue
        try:
            result = provider.fetch(query=query, limit=limit)
            errors = list(result.errors or [])
            items.append(
                base.model_copy(
                    update={
                        "status": "failed" if errors else "ok",
                        "last_checked_at": result.fetched_at.isoformat() if result.fetched_at else None,
                        "last_item_count": len(result.items),
                        "last_error": "; ".join(errors[:2]) if errors else None,
                    }
                )
            )
        except Exception as exc:  # pragma: no cover - defensive for third-party providers
            items.append(
                base.model_copy(
                    update={
                        "status": "failed",
                        "last_checked_at": utc_now().isoformat(),
                        "last_item_count": 0,
                        "last_error": str(exc),
                    }
                )
            )

    items.extend(PLACEHOLDER_SOURCES)
    return _build_report(items, demo_mode=demo_mode, notes=notes)


def write_source_coverage_report(
    report: SourceCoverageReport,
    *,
    reports_dir: str | Path = "reports",
    report_date: date | None = None,
) -> dict[str, str]:
    """Write JSON and Markdown source coverage reports."""
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    stamp = (report_date or date.today()).strftime("%Y%m%d")
    json_path = reports_path / f"source_coverage_{stamp}.json"
    md_path = reports_path / f"source_coverage_{stamp}.md"
    json_path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_source_coverage_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_source_coverage_markdown(report: SourceCoverageReport) -> str:
    """Render a source coverage report as Markdown."""
    lines = [
        "# EventAlpha 信息源覆盖状态",
        "",
        f"- generated_at: {report.generated_at}",
        f"- demo_mode: {str(report.demo_mode).lower()}",
        f"- enabled_count: {report.enabled_count}",
        f"- ok_count: {report.ok_count}",
        f"- failed_count: {report.failed_count}",
        f"- placeholder_count: {report.placeholder_count}",
        f"- latest_checked_at: {report.latest_checked_at or '暂无'}",
        "",
        "## Sources",
        "",
        "| Source | Type | Enabled | Status | Items | Last Checked | Error/Notes |",
        "|---|---|---:|---|---:|---|---|",
    ]
    for item in report.items:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(item.source_name),
                    _md(item.source_type),
                    "yes" if item.enabled else "no",
                    _md(item.status),
                    "" if item.last_item_count is None else str(item.last_item_count),
                    _md(item.last_checked_at or "暂无"),
                    _md(item.last_error or item.notes or ""),
                ]
            )
            + " |"
        )
    if report.notes:
        lines.extend(["", "## Notes", *[f"- {_md(note)}" for note in report.notes]])
    return "\n".join(lines).strip() + "\n"


def _provider_item(provider: Any) -> SourceCoverageItem:
    name = str(getattr(provider, "name", provider.__class__.__name__))
    if isinstance(provider, RSSProvider):
        return SourceCoverageItem(
            source_name=name,
            source_type="rss",
            enabled=True,
            status="not_checked",
            notes=f"RSS feed: {provider.feed_url}",
        )
    if isinstance(provider, GDELTProvider):
        return SourceCoverageItem(
            source_name=name,
            source_type="gdelt",
            enabled=True,
            status="not_checked",
            notes="GDELT DOC API provider",
        )
    return SourceCoverageItem(
        source_name=name,
        source_type="demo",
        enabled=True,
        status="not_checked",
        notes="Demo RawNews / StaticNewsProvider",
    )


def _build_report(
    items: list[SourceCoverageItem],
    *,
    demo_mode: bool,
    notes: list[str],
) -> SourceCoverageReport:
    counts = Counter(item.status for item in items)
    latest = max((item.last_checked_at or "" for item in items), default="") or None
    return SourceCoverageReport(
        demo_mode=demo_mode,
        enabled_count=sum(1 for item in items if item.enabled),
        ok_count=counts.get("ok", 0),
        failed_count=counts.get("failed", 0),
        placeholder_count=counts.get("placeholder", 0),
        latest_checked_at=latest,
        items=items,
        notes=notes,
    )


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
