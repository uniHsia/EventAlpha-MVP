"""Offline source credibility classification for news clusters."""

from __future__ import annotations

from urllib.parse import urlparse

from .schemas import SourceCredibility


OFFICIAL_HINTS = (
    "government",
    "ministry",
    "central bank",
    "federal reserve",
    "white house",
    "commerce department",
    "official",
    "商务部",
    "央行",
    "白宫",
)
MAINSTREAM_SOURCES = ("reuters", "associated press", " ap", "bbc", "nbc", "upi", "al jazeera")
FINANCIAL_SOURCES = ("bloomberg", "cnbc")
THINK_TANK_SOURCES = ("brookings", "foundation for american innovation")
ANALYSIS_SOURCES = ("tech policy press", "policy press")
AGGREGATORS = ("google news", "news.google")


class SourceCredibilityRegistry:
    """Classify source credibility using static rules and name/domain heuristics."""

    def classify(self, source_name: str, url: str | None = None) -> SourceCredibility:
        """Return source credibility classification without network access."""
        source_text = source_name.strip() or "unknown"
        haystack = f"{source_text} {_domain(url)}".casefold()
        source_key = source_text.casefold().strip()

        if any(hint in source_key for hint in AGGREGATORS):
            return SourceCredibility(
                source_name=source_text,
                source_type="aggregator",
                credibility_tier="unknown",
                rationale="Aggregator source; do not treat as original reporting source.",
            )
        if any(hint in haystack for hint in OFFICIAL_HINTS) or _official_domain(url):
            return SourceCredibility(
                source_name=source_text,
                source_type="official_source",
                credibility_tier="high",
                rationale="Source name or domain indicates official institution.",
            )
        if any(hint in haystack for hint in FINANCIAL_SOURCES):
            return SourceCredibility(
                source_name=source_text,
                source_type="financial_media",
                credibility_tier="high",
                rationale="Recognized financial media source.",
            )
        if source_key in {"ap", "associated press"} or any(hint in haystack for hint in MAINSTREAM_SOURCES):
            return SourceCredibility(
                source_name=source_text,
                source_type="mainstream_media",
                credibility_tier="high",
                rationale="Recognized mainstream media source.",
            )
        if any(hint in haystack for hint in THINK_TANK_SOURCES):
            return SourceCredibility(
                source_name=source_text,
                source_type="think_tank",
                credibility_tier="medium",
                rationale="Recognized think-tank or policy analysis source.",
            )
        if any(hint in haystack for hint in ANALYSIS_SOURCES):
            return SourceCredibility(
                source_name=source_text,
                source_type="analysis_source",
                credibility_tier="medium",
                rationale="Analysis-oriented source; useful context but not primary evidence.",
            )
        return SourceCredibility(
            source_name=source_text,
            source_type="blog_or_unknown",
            credibility_tier="unknown",
            rationale="No known credibility rule matched.",
        )


def _domain(url: str | None) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.casefold()


def _official_domain(url: str | None) -> bool:
    domain = _domain(url)
    return domain.endswith(".gov") or domain.endswith(".gov.cn") or domain.endswith(".mil")
