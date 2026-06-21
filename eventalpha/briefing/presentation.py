"""Presentation helpers for compact daily briefings."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any


BACKGROUND_SOURCE_TERMS = (
    "brookings",
    "council on foreign relations",
    "foundation",
    "think tank",
    "commentary",
    "research",
    "analysis",
)


def normalize_text(value: Any) -> str:
    """Normalize display text for deterministic grouping."""
    text = re.sub(r"[^\w\s\u4e00-\u9fff]+", " ", str(value or ""), flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip().casefold()


def latest_sort_key(row: dict[str, Any]) -> tuple[str, int]:
    """Sort rows by created timestamp and sqlite id when available."""
    created_at = str(row.get("created_at") or "")
    row_id = row.get("id") or 0
    try:
        numeric_id = int(row_id)
    except (TypeError, ValueError):
        numeric_id = 0
    return (created_at, numeric_id)


def aggregate_messages(values: list[str], *, limit: int | None = None) -> list[str]:
    """Aggregate repeated messages as 'message ×N'."""
    counter: Counter[str] = Counter()
    display: dict[str, str] = {}
    for value in values:
        message, count = _split_aggregated_message(str(value).strip())
        if not message:
            continue
        key = normalize_text(message)
        counter[key] += count
        display.setdefault(key, message)
    items = [
        f"{display[key]} ×{count}" if count > 1 else display[key]
        for key, count in counter.most_common()
    ]
    return items[:limit] if limit is not None else items


def _split_aggregated_message(message: str) -> tuple[str, int]:
    match = re.match(r"^(?P<message>.*?)(?:\s*[×xX脳]\s*(?P<count>\d+))\s*$", message)
    if not match:
        return message, 1
    return match.group("message").strip(), int(match.group("count"))


def is_background_analysis_event(event: Any) -> bool:
    """Return True when an event should be treated as background analysis."""
    if getattr(event, "lifecycle_stage", "") == "analysis_only":
        return True
    credibility = str(getattr(event, "credibility_status", "") or "")
    sources = [str(source) for source in getattr(event, "sources", [])]
    keywords = [str(keyword) for keyword in getattr(event, "dominant_keywords", [])]
    haystack = " ".join([getattr(event, "canonical_title", ""), credibility, *sources, *keywords])
    has_background_source = any(term in haystack.casefold() for term in BACKGROUND_SOURCE_TERMS)
    if not has_background_source:
        return False
    source_count = int(getattr(event, "source_count", 0) or 0)
    return not (source_count >= 2 and credibility in {"high_confidence", "multi_source_supported"})


def extract_prediction_ids_from_notes(notes: list[str]) -> list[str]:
    """Extract prediction ids mentioned in scheduler run notes."""
    results: list[str] = []
    for note in notes:
        results.extend(re.findall(r"prediction=([A-Za-z0-9_]+)", note))
    return results


def parse_datetimeish(value: Any) -> datetime | None:
    """Parse datetime-like text for optional comparisons."""
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
