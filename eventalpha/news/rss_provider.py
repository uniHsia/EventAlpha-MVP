"""RSS news provider."""

from __future__ import annotations

import calendar
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree

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
            local_path = Path(self.feed_url)
            if local_path.exists():
                try:
                    parsed = _parse_local_xml_feed(local_path)
                except Exception as parse_exc:
                    return NewsFetchResult(
                        source_name=self.name,
                        fetched_at=fetched_at,
                        items=[],
                        errors=[f"RSS fetch failed for {self.feed_url}: {parse_exc}"],
                    )
            else:
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
            summary = _clean_text(str(
                _entry_get(entry, "summary", _entry_get(entry, "description", ""))
            )) or None
            link = str(_entry_get(entry, "link", "")).strip() or None
            source = self._entry_source(entry, parsed, title)
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

    def _entry_source(self, entry: Any, parsed: Any, title: str) -> str:
        entry_source = _entry_get(_entry_get(entry, "source", {}), "title", "")
        if entry_source:
            return str(entry_source)
        feed_source = self._source_name(parsed)
        if "google news" in feed_source.casefold():
            publisher = _publisher_from_google_news_title(title)
            if publisher:
                return publisher
        return feed_source


def _load_feedparser() -> Any:
    """Import feedparser lazily so non-RSS providers can run without it."""
    import feedparser

    return feedparser


def _parse_local_xml_feed(path: Path) -> SimpleNamespace:
    """Parse a local RSS XML fixture when feedparser is unavailable."""
    root = ElementTree.parse(path).getroot()
    channel = root.find("channel")
    if channel is None:
        channel = root
    feed = {"title": _element_text(channel.find("title"))}
    entries = []
    for item in channel.findall("item"):
        entry = {
            "title": _element_text(item.find("title")),
            "summary": _element_text(item.find("description")),
            "description": _element_text(item.find("description")),
            "link": _element_text(item.find("link")),
            "published": _element_text(item.find("pubDate")),
        }
        entries.append(entry)
    return SimpleNamespace(feed=feed, entries=entries, bozo=False)


def _element_text(element: ElementTree.Element[str] | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


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
        try:
            parsed = parsedate_to_datetime(str(value))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None


def _matches_query(item: NewsItem, query_text: str, query_terms: list[str]) -> bool:
    text = f"{item.title} {item.summary or ''}".casefold()
    return query_text in text or any(term in text for term in query_terms)


def _clean_text(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _publisher_from_google_news_title(title: str) -> str | None:
    if " - " not in title:
        return None
    publisher = title.rsplit(" - ", 1)[1].strip()
    if not publisher or len(publisher.split()) > 8:
        return None
    return publisher
