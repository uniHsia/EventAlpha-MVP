"""Lightweight event clustering for candidate news."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from .filters import KEYWORD_GROUPS
from .schemas import EventCluster, NewsItem


STOPWORDS = {
    "about",
    "after",
    "against",
    "affect",
    "affects",
    "america",
    "american",
    "amid",
    "and",
    "are",
    "article",
    "articles",
    "blank",
    "ban",
    "bill",
    "china",
    "chinese",
    "com",
    "concern",
    "concerns",
    "for",
    "from",
    "google",
    "has",
    "href",
    "html",
    "http",
    "https",
    "into",
    "its",
    "may",
    "new",
    "news",
    "nbsp",
    "over",
    "says",
    "supply",
    "the",
    "that",
    "this",
    "to",
    "us",
    "usa",
    "with",
    "would",
}


class NewsClusterer:
    """Cluster candidate news with URL and keyword overlap rules."""

    def __init__(self, similarity_threshold: float = 0.42) -> None:
        self.similarity_threshold = similarity_threshold

    def cluster(self, items: list[NewsItem]) -> list[EventCluster]:
        """Return verified-ready event clusters from candidate items."""
        clusters: list[list[NewsItem]] = []
        reasons: list[list[str]] = []

        for item in sorted(items, key=_item_time, reverse=True):
            placed = False
            for index, cluster_items in enumerate(clusters):
                reason = self._match_reason(item, cluster_items)
                if reason:
                    cluster_items.append(item)
                    reasons[index].append(reason)
                    placed = True
                    break
            if not placed:
                clusters.append([item])
                reasons.append(["seed item"])

        return sorted(
            [
                self._build_cluster(cluster_items, cluster_reasons)
                for cluster_items, cluster_reasons in zip(clusters, reasons)
            ],
            key=lambda cluster: (
                cluster.confidence,
                cluster.source_count,
                cluster.last_seen_at or datetime.min,
                len(cluster.items),
            ),
            reverse=True,
        )

    def _match_reason(self, item: NewsItem, cluster_items: list[NewsItem]) -> str | None:
        item_url = _normalized_url(item)
        if item_url and any(item_url == _normalized_url(existing) for existing in cluster_items):
            return f"url match: {item_url}"

        item_keywords = extract_keywords(item)
        cluster_keywords = set().union(*(extract_keywords(existing) for existing in cluster_items))
        score = jaccard(item_keywords, cluster_keywords)
        if score >= self.similarity_threshold:
            return f"keyword overlap {score:.2f} >= {self.similarity_threshold:.2f}"
        overlap_count = len(item_keywords & cluster_keywords)
        if overlap_count >= 4:
            return f"keyword overlap count {overlap_count} >= 4"
        return None

    def _build_cluster(self, items: list[NewsItem], debug_reasons: list[str]) -> EventCluster:
        keywords = _dominant_keywords(items)
        canonical_item = max(items, key=_title_score)
        summary_item = max(items, key=lambda item: len(item.raw_text or item.summary or ""))
        source_names = _unique(item.source for item in items)
        return EventCluster(
            canonical_title=canonical_item.title,
            canonical_summary=summary_item.raw_text or summary_item.summary,
            items=items,
            sources=source_names,
            source_count=len(source_names),
            mainstream_source_count=sum(1 for item in items if _is_mainstream(item)),
            dominant_keywords=keywords,
            candidate_event_type=_candidate_event_type(keywords),
            confidence=_cluster_base_confidence(items, source_names),
            debug_reasons=_unique(debug_reasons),
        )


def extract_keywords(item: NewsItem) -> set[str]:
    """Extract simple English words and known Chinese/topic keywords."""
    title = _strip_publisher_suffix(item.title)
    text = f"{title} {item.summary or ''} {item.raw_text or ''}".casefold()
    keywords = {
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if len(token) >= 3 and token not in STOPWORDS
    }
    for group, values in KEYWORD_GROUPS.items():
        if any(value.casefold() in text for value in values):
            keywords.add(group)
    return keywords


def jaccard(left: set[str], right: set[str]) -> float:
    """Return Jaccard similarity for two keyword sets."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _dominant_keywords(items: list[NewsItem]) -> list[str]:
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(extract_keywords(item))
    return [keyword for keyword, _ in counter.most_common(8)]


def _candidate_event_type(keywords: list[str]) -> str | None:
    for keyword in keywords:
        if keyword in KEYWORD_GROUPS:
            return keyword
    return None


def _cluster_base_confidence(items: list[NewsItem], sources: list[str]) -> float:
    return min(0.35 + (0.12 * max(len(sources) - 1, 0)) + (0.03 * max(len(items) - 1, 0)), 0.72)


def _is_mainstream(item: NewsItem) -> bool:
    text = f"{item.source} {item.source_type}".casefold()
    known = ("reuters", "ap", "bloomberg", "bbc", "nbc", "al jazeera", "upi", "mainstream_media")
    return item.source_type == "mainstream_media" or any(name in text for name in known)


def _item_time(item: NewsItem) -> datetime:
    return item.published_at or item.fetched_at


def _title_score(item: NewsItem) -> tuple[int, datetime]:
    return (len(extract_keywords(item)), _item_time(item))


def _normalized_url(item: NewsItem) -> str:
    return (item.url or "").strip().rstrip("/").casefold()


def _strip_publisher_suffix(title: str) -> str:
    if " - " not in title:
        return title
    head, tail = title.rsplit(" - ", 1)
    if len(tail.split()) <= 6:
        return head
    return title


def _unique(values) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
