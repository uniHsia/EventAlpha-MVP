"""Deduplication helpers for candidate news."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import NewsItem


@dataclass(frozen=True)
class NewsDedupResult:
    """Result of deduplicating news items."""

    items: list[NewsItem]
    before_count: int
    after_count: int
    duplicate_count: int


def deduplicate_news(items: list[NewsItem]) -> NewsDedupResult:
    """Deduplicate news by URL, falling back to normalized title."""
    deduped: list[NewsItem] = []
    seen: set[str] = set()
    for item in items:
        key = _dedup_key(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return NewsDedupResult(
        items=deduped,
        before_count=len(items),
        after_count=len(deduped),
        duplicate_count=len(items) - len(deduped),
    )


def _dedup_key(item: NewsItem) -> str:
    if item.url:
        return "url:" + str(item.url).strip().rstrip("/").casefold()
    return "title:" + re.sub(r"\s+", " ", item.title.strip()).casefold()
