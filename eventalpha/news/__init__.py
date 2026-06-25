"""News collection utilities for EventAlpha."""

from .base import NewsProvider
from .claim_consistency import ClaimConsistencyService
from .claim_extraction import ClusterClaimExtractor
from .cluster_raw_news_converter import event_cluster_to_raw_news
from .cluster_credibility import ClusterCredibilityService
from .cluster_verification import ClusterVerificationService
from .clustering import NewsClusterer
from .credibility_mapping import NormalizedClusterCredibility, normalize_cluster_credibility
from .dedup import NewsDedupResult, deduplicate_news
from .filters import NewsFilterResult, NewsKeywordFilter
from .gdelt_provider import GDELTProvider
from .lifecycle import (
    EventLifecycleUpdate,
    EventMatchResult,
    EventTimelineEntry,
    TrackedEvent,
    make_event_key,
    make_tracked_event_id,
)
from .lifecycle_matching import EventLifecycleMatcher
from .lifecycle_store import DEFAULT_LIFECYCLE_STORE_PATH, EventLifecycleStore
from .lifecycle_update import EventLifecycleUpdater
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
from .source_coverage import (
    SourceCoverageItem,
    SourceCoverageReport,
    collect_source_coverage,
    write_source_coverage_report,
)
from .source_registry import NewsSourceRegistry, build_mock_registry, build_real_registry
from .search_quality import SearchQualityReport, build_search_quality_report, write_search_quality_report

__all__ = [
    "ClaimConsistencyService",
    "ClaimConsistencySummary",
    "ClusterClaim",
    "ClusterClaimExtractor",
    "ClusterCredibilityReport",
    "ClusterCredibilityService",
    "ClusterVerificationService",
    "NormalizedClusterCredibility",
    "EventCluster",
    "EventLifecycleMatcher",
    "EventLifecycleStore",
    "EventLifecycleUpdate",
    "EventLifecycleUpdater",
    "EventMatchResult",
    "EventTimelineEntry",
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
    "SourceCoverageItem",
    "SourceCoverageReport",
    "SearchQualityReport",
    "TrackedEvent",
    "DEFAULT_LIFECYCLE_STORE_PATH",
    "build_mock_registry",
    "build_real_registry",
    "build_search_quality_report",
    "collect_source_coverage",
    "deduplicate_news",
    "event_cluster_to_raw_news",
    "normalize_cluster_credibility",
    "make_claim_id",
    "make_cluster_id",
    "make_event_key",
    "make_news_id",
    "make_tracked_event_id",
    "news_item_to_raw_news",
    "write_search_quality_report",
    "write_source_coverage_report",
]
