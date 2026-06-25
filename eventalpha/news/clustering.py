"""Lightweight event clustering for candidate news."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher

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
    """Cluster candidate news with conservative event-matching rules."""

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

        cluster_keywords = set().union(*(extract_keywords(existing) for existing in cluster_items))
        item_keywords = extract_keywords(item)
        canonical = max(cluster_items, key=_title_score)
        title_similarity = _title_similarity(item.title, canonical.title)
        keyword_score = jaccard(item_keywords, cluster_keywords)
        entity_overlap = len(_entity_tokens(item) & set().union(*(_entity_tokens(existing) for existing in cluster_items)))
        event_type_match = _coarse_event_type(item) == _coarse_cluster_event_type(cluster_items)
        time_close = _hours_apart(item, canonical) <= 48
        action_match = bool(_action_tokens(item) & set().union(*(_action_tokens(existing) for existing in cluster_items)))
        same_source = item.source in {existing.source for existing in cluster_items}

        if title_similarity >= 0.84 and action_match and time_close:
            return f"title/action/time match {title_similarity:.2f}"
        if (
            not same_source
            and title_similarity >= 0.72
            and entity_overlap >= 1
            and event_type_match
            and time_close
            and action_match
        ):
            return (
                "cross-source event match "
                f"title={title_similarity:.2f} entity={entity_overlap} keyword={keyword_score:.2f}"
            )
        return None

    def _build_cluster(self, items: list[NewsItem], debug_reasons: list[str]) -> EventCluster:
        keywords = _dominant_keywords(items)
        canonical_item = max(items, key=_title_score)
        summary_item = max(items, key=lambda item: len(item.raw_text or item.summary or ""))
        source_names = _unique(item.source for item in items)
        cluster_type = _cluster_type(items, source_names, canonical_item, keywords)
        unique_source_count = len(source_names)
        return EventCluster(
            canonical_title=canonical_item.title,
            canonical_summary=summary_item.raw_text or summary_item.summary,
            items=items,
            sources=source_names,
            source_count=unique_source_count,
            item_count=len(items),
            unique_source_count=unique_source_count,
            mainstream_source_count=sum(1 for item in items if _is_mainstream(item)),
            dominant_keywords=keywords,
            candidate_event_type=_candidate_event_type(keywords),
            cluster_type=cluster_type,
            independent_confirmation=(
                unique_source_count >= 2 and cluster_type in {"multi_source_event", "official_update_cluster"}
            ),
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


def _cluster_type(
    items: list[NewsItem],
    sources: list[str],
    canonical_item: NewsItem,
    keywords: list[str],
) -> str:
    unique_source_count = len(sources)
    title_text = canonical_item.title.casefold()
    analysis_like = sum(1 for item in items if _is_analysis_like(item))
    official_like = any(item.source_type == "official" or _looks_official(item) for item in items)
    same_source = unique_source_count <= 1 and len(items) > 1

    if analysis_like == len(items) or _looks_analysis_digest(title_text, keywords):
        return "analysis_digest"
    if official_like and unique_source_count >= 2:
        return "official_update_cluster"
    if unique_source_count >= 2:
        return "multi_source_event"
    if same_source:
        return "same_source_topic_cluster"
    return "single_news_event"


def _coarse_event_type(item: NewsItem) -> str | None:
    return _candidate_event_type(_dominant_keywords([item]))


def _coarse_cluster_event_type(items: list[NewsItem]) -> str | None:
    return _candidate_event_type(_dominant_keywords(items))


def _entity_tokens(item: NewsItem) -> set[str]:
    text = _strip_publisher_suffix(item.title)
    tokens = {
        token
        for token in re.findall(r"[A-Z][A-Za-z0-9&.-]+", text)
        if len(token) >= 3
    }
    return {token.casefold() for token in tokens}


ACTION_WORDS = {
    "ban",
    "bans",
    "restrict",
    "restriction",
    "restricts",
    "approve",
    "approves",
    "launch",
    "launches",
    "announce",
    "announces",
    "update",
    "updates",
    "raise",
    "raises",
    "cut",
    "cuts",
    "sanction",
    "sanctions",
    "expand",
    "expands",
    "delay",
    "delays",
}


def _action_tokens(item: NewsItem) -> set[str]:
    text = f"{item.title} {item.summary or ''}".casefold()
    return {token for token in re.findall(r"[a-z]+", text) if token in ACTION_WORDS}


def _title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _strip_publisher_suffix(left).casefold(), _strip_publisher_suffix(right).casefold()).ratio()


def _hours_apart(left: NewsItem, right: NewsItem) -> float:
    left_time = _item_time(left)
    right_time = _item_time(right)
    return abs((left_time - right_time).total_seconds()) / 3600.0


def _is_analysis_like(item: NewsItem) -> bool:
    text = f"{item.source} {item.source_type} {item.title}".casefold()
    source_name = item.source.casefold()
    if "semiconductor engineering" in source_name:
        return True
    return item.source_type == "research_report" or any(
        marker in text
        for marker in (
            "analysis",
            "opinion",
            "explains",
            "strategy",
            "digest",
            "think tank",
            "brookings",
            "policy",
            "engineering",
        )
    )


def _looks_official(item: NewsItem) -> bool:
    text = f"{item.source} {item.title}".casefold()
    return any(marker in text for marker in ("ministry", "department", "federal reserve", "white house", "official"))


def _looks_analysis_digest(title_text: str, keywords: list[str]) -> bool:
    if "semiconductor engineering" in title_text:
        return True
    analysis_markers = ("analysis", "explains", "strategy", "why", "digest", "outlook")
    return any(marker in title_text for marker in analysis_markers) and len(keywords) >= 2


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
