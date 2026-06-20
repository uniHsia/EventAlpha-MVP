"""RSS news provider."""

from __future__ import annotations

import calendar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eventalpha.schemas.base import utc_now

from .schemas import NewsFetchResult, NewsItem


class RSSProvider:
    """Fetch and normalize items from an RSS or Atom feed."""

    def __init__(
        self,
        feed_url: str,
        name: str = "rss",
        source_type: str = "mainstream_media",
        language: str | None = None,
        country: str | None = None,
    ) -> None:
        self.feed_url = feed_url
        self.name = name
        self.source_type = source_type
        self.language = language
        self.country = country

    def fetch(self, query: str | None = None, limit: int = 20) -> NewsFetchResult:
        """Fetch and normalize RSS entries."""
        fetched_at = utc_now()
        errors: list[str] = []
        items: list[NewsItem] = []
        try:
            feedparser = _load_feedparser()
            parsed = feedparser.parse(self.feed_url)
        except ImportError as exc:
            return NewsFetchResult(
                source_name=self.name,
                fetched_at=fetched_at,
                items=[],
                errors=[f"RSS dependency missing for {self.feed_url}: {exc}"],
            )
        except Exception as exc:
            return NewsFetchResult(
                source_name=self.name,
                fetched_at=fetched_at,
                items=[],
                errors=[f"RSS fetch failed for {self.feed_url}: {exc}"],
            )

        if getattr(parsed, "bozo", False):
            errors.append(f"RSS parse warning for {self.feed_url}: {getattr(parsed, 'bozo_exception', '')}")

        for entry in list(getattr(parsed, "entries", []))[:limit]:
            title = str(_entry_get(entry, "title", "")).strip()
            if not title:
                continue
            summary = str(
                _entry_get(entry, "summary", _entry_get(entry, "description", ""))
            ).strip() or None
            link = str(_entry_get(entry, "link", "")).strip() or None
            source = self._source_name(parsed)
            items.append(
                NewsItem(
                    title=title,
                    summary=summary,
                    url=link,
                    source=source,
                    source_type=self.source_type,
                    published_at=_published_at(entry),
                    language=self.language,
                    country=self.country,
                    raw_text=summary,
                    fetched_at=fetched_at,
                )
            )

        if query:
            query_text = query.casefold()
            query_terms = [
                term
                for term in query_text.replace('"', " ").split()
                if len(term) >= 3
            ]
            items = [
                item
                for item in items
                if _matches_query(item, query_text, query_terms)
            ]
            if not items:
                errors.append("RSS query matched no items.")

        return NewsFetchResult(
            source_name=self.name,
            fetched_at=fetched_at,
            items=items[:limit],
            errors=errors,
        )

    def _source_name(self, parsed: Any) -> str:
        feed = getattr(parsed, "feed", {})
        title = _entry_get(feed, "title", "")
        if title:
            return str(title)
        path_name = Path(str(self.feed_url)).stem
        return path_name or self.name


def _load_feedparser() -> Any:
    """Import feedparser lazily so non-RSS providers can run without it."""
    import feedparser

    return feedparser


def _entry_get(entry: Any, key: str, default: Any = None) -> Any:
    if hasattr(entry, "get"):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _published_at(entry: Any) -> datetime | None:
    parsed = _entry_get(entry, "published_parsed") or _entry_get(entry, "updated_parsed")
    if parsed:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    value = _entry_get(entry, "published") or _entry_get(entry, "updated")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _matches_query(item: NewsItem, query_text: str, query_terms: list[str]) -> bool:
    text = f"{item.title} {item.summary or ''}".casefold()
    return query_text in text or any(term in text for term in query_terms)
