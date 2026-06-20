"""News collection utilities for EventAlpha."""

from .base import NewsProvider
from .claim_consistency import ClaimConsistencyService
from .claim_extraction import ClusterClaimExtractor
from .cluster_raw_news_converter import event_cluster_to_raw_news
from .cluster_credibility import ClusterCredibilityService
from .cluster_verification import ClusterVerificationService
from .clustering import NewsClusterer
from .dedup import NewsDedupResult, deduplicate_news
from .filters import NewsFilterResult, NewsKeywordFilter
from .gdelt_provider import GDELTProvider
from .raw_news_converter import news_item_to_raw_news
from .rss_provider import RSSProvider
from .official_evidence import OfficialEvidenceHeuristic
from .schemas import (
    ClaimConsistencySummary,
    ClusterClaim,
    ClusterCredibilityReport,
    EventCluster,
    NewsFetchResult,
    NewsItem,
    SourceCredibility,
    make_claim_id,
    make_cluster_id,
    make_news_id,
)
from .source_credibility import SourceCredibilityRegistry
from .source_registry import NewsSourceRegistry, build_mock_registry, build_real_registry

__all__ = [
    "ClaimConsistencyService",
    "ClaimConsistencySummary",
    "ClusterClaim",
    "ClusterClaimExtractor",
    "ClusterCredibilityReport",
    "ClusterCredibilityService",
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
    "OfficialEvidenceHeuristic",
    "RSSProvider",
    "SourceCredibility",
    "SourceCredibilityRegistry",
    "build_mock_registry",
    "build_real_registry",
    "deduplicate_news",
    "event_cluster_to_raw_news",
    "make_claim_id",
    "make_cluster_id",
    "make_news_id",
    "news_item_to_raw_news",
]
