"""Registry for coordinating multiple news providers."""

from __future__ import annotations

from dataclasses import dataclass

from eventalpha.schemas.base import utc_now

from .base import NewsProvider
from .gdelt_provider import GDELTProvider
from .rss_provider import RSSProvider
from .schemas import NewsFetchResult, NewsItem, SourceRegistryEntry


DEFAULT_RSS_FEEDS = (
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.sec.gov/news/pressreleases.rss",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://semiengineering.com/feed/",
)


class NewsSourceRegistry:
    """Fetch news from multiple providers while isolating single-source failures."""

    def __init__(
        self,
        providers: list[NewsProvider],
        source_entries: list[SourceRegistryEntry] | None = None,
    ) -> None:
        self.providers = providers
        self.source_entries = list(source_entries or [])

    def fetch_all(self, query: str | None = None, limit_per_source: int = 20) -> NewsFetchResult:
        """Fetch from all providers and aggregate items/errors."""
        fetched_at = utc_now()
        items: list[NewsItem] = []
        errors: list[str] = []
        for provider in self.providers:
            try:
                result = provider.fetch(query=query, limit=limit_per_source)
                items.extend(result.items)
                errors.extend(result.errors)
            except Exception as exc:
                errors.append(f"{getattr(provider, 'name', provider.__class__.__name__)} failed: {exc}")
        return NewsFetchResult(
            source_name="news_registry",
            fetched_at=fetched_at,
            items=items,
            errors=errors,
        )


@dataclass
class StaticNewsProvider:
    """Deterministic offline provider for tests and default scout runs."""

    name: str
    items: list[NewsItem]
    source_type: str = "demo"
    region: str | None = "global"
    language: str | None = "en"
    credibility_base: float = 0.3
    fetch_mode: str = "offline_fixture"

    def fetch(self, query: str | None = None, limit: int = 20) -> NewsFetchResult:
        """Return static items without network access."""
        filtered = self.items
        if query:
            query_text = query.casefold()
            filtered = [
                item
                for item in self.items
                if query_text in f"{item.title} {item.summary or ''}".casefold()
            ]
            if not filtered:
                filtered = self.items
        return NewsFetchResult(
            source_name=self.name,
            items=filtered[:limit],
            errors=[],
        )


def build_mock_registry() -> NewsSourceRegistry:
    """Build a deterministic offline news registry."""
    items = [
        NewsItem(
            title="US expands AI chip export controls on advanced GPU sales",
            summary="The policy may affect AI chip supply chains and domestic semiconductor substitutes.",
            url="mock://news/ai-chip-export-control",
            source="Mock Global News",
            source_type="mainstream_media",
            language="en",
            country="US",
            tags=["mock"],
        ),
        NewsItem(
            title="美国宣布对部分进口商品加征关税",
            summary="关税政策涉及新能源设备和制造业零部件，市场关注出口链和进口替代方向。",
            url="mock://news/tariff-trade-policy",
            source="Mock Finance CN",
            source_type="mainstream_media",
            language="zh",
            country="US",
            tags=["mock"],
        ),
        NewsItem(
            title="Middle East conflict raises oil supply concerns",
            summary="Red Sea attacks and regional conflict may affect crude oil logistics.",
            url="mock://news/middle-east-oil",
            source="Mock Wire",
            source_type="mainstream_media",
            language="en",
            country="AE",
            tags=["mock"],
        ),
        NewsItem(
            title="央行宣布下调政策利率",
            summary="降息后仍需观察收益率曲线、汇率和市场预期变化。",
            url="mock://news/rate-cut",
            source="Mock Central Bank",
            source_type="official",
            language="zh",
            country="CN",
            tags=["mock"],
        ),
        NewsItem(
            title="日本发生强震，半导体材料供应链扰动待确认",
            summary="地震后部分工厂运行情况仍需确认，供应链影响需要后续验证。",
            url="mock://news/earthquake-supply-chain",
            source="Mock Asia News",
            source_type="mainstream_media",
            language="zh",
            country="JP",
            tags=["mock"],
        ),
        NewsItem(
            title="Local sports team announces new stadium food options",
            summary="A lifestyle story unrelated to market-moving event discovery.",
            url="mock://news/local-sports-food",
            source="Mock Local",
            source_type="mainstream_media",
            language="en",
            country="US",
            tags=["mock"],
        ),
    ]
    provider = StaticNewsProvider(name="mock_news", items=items)
    return NewsSourceRegistry(
        [provider],
        source_entries=[
            SourceRegistryEntry(
                source_name=provider.name,
                source_type=provider.source_type,
                enabled=True,
                region=provider.region,
                language=provider.language,
                credibility_base=provider.credibility_base,
                fetch_mode=provider.fetch_mode,
                notes="Offline fixture for deterministic scout/demo runs.",
            )
        ],
    )


def build_real_registry(
    rss_feeds: list[str] | None = None,
    source: str = "all",
) -> NewsSourceRegistry:
    """Build real providers. Call this only when --real-fetch is explicit."""
    if source not in {"all", "gdelt", "rss"}:
        raise ValueError("source must be one of: all, gdelt, rss")

    providers: list[NewsProvider] = []
    entries: list[SourceRegistryEntry] = []
    if source in {"all", "gdelt"}:
        provider = GDELTProvider()
        setattr(provider, "source_type", "gdelt")
        setattr(provider, "region", "global")
        setattr(provider, "language", None)
        setattr(provider, "credibility_base", 0.62)
        setattr(provider, "fetch_mode", "api")
        providers.append(provider)
        entries.append(
            SourceRegistryEntry(
                source_name=provider.name,
                source_type="gdelt",
                enabled=True,
                region="global",
                language=None,
                credibility_base=0.62,
                fetch_mode="api",
                notes="GDELT DOC API query provider.",
            )
        )
    if source in {"all", "rss"}:
        for index, feed_url in enumerate(rss_feeds or list(DEFAULT_RSS_FEEDS)):
            source_name, source_type, region, language, credibility_base, notes = _rss_metadata(feed_url, index)
            providers.append(
                RSSProvider(
                    feed_url=feed_url,
                    name=source_name,
                    source_type=source_type,
                    language=language,
                )
            )
            provider = providers[-1]
            setattr(provider, "region", region)
            setattr(provider, "credibility_base", credibility_base)
            setattr(provider, "fetch_mode", "rss")
            entries.append(
                SourceRegistryEntry(
                    source_name=source_name,
                    source_type=source_type,
                    enabled=True,
                    region=region,
                    language=language,
                    credibility_base=credibility_base,
                    fetch_mode="rss",
                    notes=notes,
                )
            )
    return NewsSourceRegistry(providers, source_entries=entries)


def _rss_metadata(feed_url: str, index: int) -> tuple[str, str, str | None, str | None, float, str]:
    normalized = str(feed_url).casefold()
    if "sec.gov" in normalized:
        return (
            "sec_press_releases",
            "official",
            "US",
            "en",
            0.9,
            "SEC official press release RSS.",
        )
    if "federalreserve.gov" in normalized:
        return (
            "federal_reserve_press",
            "official",
            "US",
            "en",
            0.9,
            "Federal Reserve official press release feed.",
        )
    if "semiengineering.com" in normalized:
        return (
            "semi_engineering_feed",
            "industry_source",
            "global",
            "en",
            0.68,
            "Semiconductor industry public RSS feed.",
        )
    if "bbc" in normalized:
        return (
            "bbc_business",
            "mainstream_media",
            "global",
            "en",
            0.72,
            "BBC Business RSS feed.",
        )
    return (
        f"rss_{index + 1}",
        "mainstream_media",
        None,
        None,
        0.6,
        f"Custom RSS feed: {feed_url}",
    )
