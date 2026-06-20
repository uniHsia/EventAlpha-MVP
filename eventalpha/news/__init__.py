"""News collection utilities for EventAlpha."""

from .base import NewsProvider
from .cluster_raw_news_converter import event_cluster_to_raw_news
from .cluster_verification import ClusterVerificationService
from .clustering import NewsClusterer
from .dedup import NewsDedupResult, deduplicate_news
from .filters import NewsFilterResult, NewsKeywordFilter
from .gdelt_provider import GDELTProvider
from .raw_news_converter import news_item_to_raw_news
from .rss_provider import RSSProvider
from .schemas import EventCluster, NewsFetchResult, NewsItem, make_cluster_id, make_news_id
from .source_registry import NewsSourceRegistry, build_mock_registry, build_real_registry

__all__ = [
    "ClusterVerificationService",
    "EventCluster",
    "GDELTProvider",
    "NewsDedupResult",
    "NewsFetchResult",
    "NewsFilterResult",
    "NewsItem",
    "NewsClusterer",
    "NewsKeywordFilter",
    "NewsProvider",
    "NewsSourceRegistry",
    "RSSProvider",
    "build_mock_registry",
    "build_real_registry",
    "deduplicate_news",
    "event_cluster_to_raw_news",
    "make_cluster_id",
    "make_news_id",
    "news_item_to_raw_news",
]
