"""Convert collected news items to EventAlpha RawNews."""

from __future__ import annotations

from eventalpha.schemas import RawNews

from .schemas import NewsItem


def news_item_to_raw_news(item: NewsItem) -> RawNews:
    """Convert a standardized NewsItem to the existing RawNews schema."""
    raw_text = item.raw_text or item.summary or item.title
    metadata = {
        "news_id": item.news_id,
        "fetched_at": item.fetched_at.isoformat(),
    }
    if item.url:
        metadata["url"] = item.url
    if item.country:
        metadata["country"] = item.country
    if item.tags:
        metadata["tags"] = ",".join(item.tags)

    return RawNews(
        raw_id=item.news_id,
        title=item.title,
        source=item.source,
        source_type=item.source_type if item.source_type in _RAW_SOURCE_TYPES else "unknown",
        publish_time=item.published_at or item.fetched_at,
        url=item.url,
        language=item.language or "unknown",
        raw_text=raw_text,
        metadata=metadata,
    )


_RAW_SOURCE_TYPES = {
    "official",
    "mainstream_media",
    "social_media",
    "research_report",
    "unknown",
}
