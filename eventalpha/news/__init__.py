"""News collection utilities for EventAlpha."""

from .base import NewsProvider
from .dedup import NewsDedupResult, deduplicate_news
from .filters import NewsFilterResult, NewsKeywordFilter
from .gdelt_provider import GDELTProvider
from .raw_news_converter import news_item_to_raw_news
from .rss_provider import RSSProvider
from .schemas import NewsFetchResult, NewsItem, make_news_id
from .source_registry import NewsSourceRegistry, build_mock_registry, build_real_registry

__all__ = [
    "GDELTProvider",
    "NewsDedupResult",
    "NewsFetchResult",
    "NewsFilterResult",
    "NewsItem",
    "NewsKeywordFilter",
    "NewsProvider",
    "NewsSourceRegistry",
    "RSSProvider",
    "build_mock_registry",
    "build_real_registry",
    "deduplicate_news",
    "make_news_id",
    "news_item_to_raw_news",
]
