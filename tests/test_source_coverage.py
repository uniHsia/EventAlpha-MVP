"""Tests for source coverage reporting."""

from __future__ import annotations

from eventalpha.news import NewsFetchResult, NewsItem, NewsSourceRegistry
from eventalpha.news.source_coverage import collect_source_coverage


class _FailingProvider:
    name = "failing_source"

    def fetch(self, query=None, limit=20):
        return NewsFetchResult(source_name=self.name, items=[], errors=["failed locally"])


class _OkProvider:
    name = "ok_demo"

    def fetch(self, query=None, limit=20):
        return NewsFetchResult(
            source_name=self.name,
            items=[NewsItem(title="AI chip export control", source="Mock", source_type="mainstream_media")],
            errors=[],
        )


def test_source_coverage_marks_ok_failed_and_placeholder() -> None:
    report = collect_source_coverage(
        registry=NewsSourceRegistry([_OkProvider(), _FailingProvider()]),
        demo_mode=True,
    )

    statuses = {item.source_name: item.status for item in report.items}

    assert statuses["ok_demo"] == "ok"
    assert statuses["failing_source"] == "failed"
    assert report.placeholder_count == 3
    assert report.demo_mode is True
