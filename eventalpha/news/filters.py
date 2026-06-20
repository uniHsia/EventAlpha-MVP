"""Keyword filters for event-discovery candidate news."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import NewsItem


KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    "conflict": (
        "war",
        "conflict",
        "attack",
        "red sea",
        "middle east",
        "战争",
        "冲突",
        "袭击",
        "红海",
        "中东",
    ),
    "rate_policy": (
        "rate cut",
        "rate hike",
        "interest rate",
        "central bank",
        "federal reserve",
        "fed",
        "降息",
        "加息",
        "利率",
        "央行",
        "美联储",
    ),
    "trade_policy": (
        "tariff",
        "trade",
        "export control",
        "sanction",
        "sanctions",
        "关税",
        "贸易",
        "出口管制",
        "制裁",
    ),
    "natural_disaster": (
        "earthquake",
        "typhoon",
        "flood",
        "disaster",
        "地震",
        "台风",
        "洪水",
        "灾害",
    ),
    "technology": (
        "ai chip",
        "gpu",
        "semiconductor",
        "tech breakthrough",
        "technology breakthrough",
        "AI 芯片",
        "AI芯片",
        "半导体",
        "科技突破",
    ),
    "election_policy": (
        "election",
        "policy",
        "vote",
        "选举",
        "政策",
    ),
    "commodity_supply_chain": (
        "oil",
        "crude",
        "gold",
        "supply chain",
        "原油",
        "黄金",
        "供应链",
    ),
}


@dataclass(frozen=True)
class NewsFilterResult:
    """Keyword filter result for candidate news."""

    candidates: list[NewsItem]
    rejected: list[NewsItem]
    reasons: dict[str, list[str]]
    before_count: int
    after_count: int


class NewsKeywordFilter:
    """Loose keyword filter for candidate event news."""

    def __init__(self, keyword_groups: dict[str, tuple[str, ...]] | None = None) -> None:
        self.keyword_groups = keyword_groups or KEYWORD_GROUPS

    def filter_items(self, items: list[NewsItem]) -> NewsFilterResult:
        """Return candidate items and match reasons."""
        candidates: list[NewsItem] = []
        rejected: list[NewsItem] = []
        reasons: dict[str, list[str]] = {}

        for item in items:
            matched = self.match_reasons(item)
            if matched:
                candidates.append(item.model_copy(update={"tags": _merge_tags(item.tags, matched)}))
                reasons[item.news_id] = matched
            else:
                rejected.append(item)

        return NewsFilterResult(
            candidates=candidates,
            rejected=rejected,
            reasons=reasons,
            before_count=len(items),
            after_count=len(candidates),
        )

    def match_reasons(self, item: NewsItem) -> list[str]:
        """Return keyword group names matched by a news item."""
        text = f"{item.title} {item.summary or ''} {item.raw_text or ''}".casefold()
        matched: list[str] = []
        for group, keywords in self.keyword_groups.items():
            if any(_keyword_matches(text, keyword) for keyword in keywords):
                matched.append(group)
        return matched


def _merge_tags(existing: list[str], matched: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in list(existing) + [f"filter:{item}" for item in matched]:
        if value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results


def _keyword_matches(text: str, keyword: str) -> bool:
    normalized = keyword.casefold()
    if normalized.isascii():
        escaped = re.escape(normalized)
        pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
        return re.search(pattern, text) is not None
    return normalized in text
