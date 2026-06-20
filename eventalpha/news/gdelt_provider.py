"""GDELT DOC API news provider."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import time
from typing import Any

import requests

from eventalpha.schemas.base import utc_now

from .schemas import NewsFetchResult, NewsItem


GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTProvider:
    """Fetch candidate news from the GDELT DOC API."""

    name = "gdelt"

    def __init__(
        self,
        api_url: str = GDELT_DOC_API_URL,
        request_get: Callable[..., Any] | None = None,
        timeout: int = 15,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.0,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.api_url = api_url
        self.request_get = request_get or requests.get
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.sleeper = sleeper or time.sleep

    def fetch(self, query: str | None = None, limit: int = 20) -> NewsFetchResult:
        """Fetch and normalize GDELT articles."""
        fetched_at = utc_now()
        params = {
            "query": query or "event",
            "mode": "ArtList",
            "format": "json",
            "maxrecords": limit,
        }
        last_rate_limit_message = ""
        payload: dict[str, Any] | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._request(params)
            except Exception as exc:
                return NewsFetchResult(
                    source_name=self.name,
                    fetched_at=fetched_at,
                    items=[],
                    errors=[f"GDELT request failed: {exc}"],
                )
            status_code = getattr(response, "status_code", 200)
            if status_code == 429:
                retry_after = _retry_after_seconds(response)
                wait_seconds = retry_after if retry_after is not None else self.retry_backoff_seconds * (2**attempt)
                last_rate_limit_message = (
                    "GDELT rate limited request with status 429"
                    f" on attempt {attempt + 1}/{self.max_retries + 1}"
                )
                if attempt < self.max_retries:
                    self.sleeper(wait_seconds)
                    continue
                return NewsFetchResult(
                    source_name=self.name,
                    fetched_at=fetched_at,
                    items=[],
                    errors=[
                        f"{last_rate_limit_message}. Retry later, lower --limit, "
                        "or rely on RSS/mock fallback for this scout run."
                    ],
                )
            if status_code >= 400:
                return NewsFetchResult(
                    source_name=self.name,
                    fetched_at=fetched_at,
                    items=[],
                    errors=[f"GDELT request failed with status {status_code}"],
                )
            try:
                payload = response.json()
            except Exception as exc:
                if attempt < self.max_retries:
                    self.sleeper(self.retry_backoff_seconds * (2**attempt))
                    continue
                return NewsFetchResult(
                    source_name=self.name,
                    fetched_at=fetched_at,
                    items=[],
                    errors=[
                        "GDELT returned a non-JSON or empty response "
                        f"after {self.max_retries + 1} attempts: {exc}. "
                        "This can happen during throttling or transient upstream errors; "
                        "retry later or lower --limit."
                    ],
                )
            break

        articles = payload.get("articles", []) if isinstance(payload, dict) else []
        items: list[NewsItem] = []
        for article in articles[:limit]:
            title = str(article.get("title") or "").strip()
            if not title:
                continue
            url = article.get("url")
            source = str(article.get("source") or article.get("domain") or "GDELT")
            items.append(
                NewsItem(
                    title=title,
                    summary=article.get("summary"),
                    url=str(url).strip() if url else None,
                    source=source,
                    source_type="mainstream_media",
                    published_at=_parse_gdelt_datetime(article.get("seendate")),
                    language=article.get("language"),
                    country=article.get("sourceCountry"),
                    raw_text=article.get("summary") or title,
                    fetched_at=fetched_at,
                    tags=["gdelt"],
                )
            )

        return NewsFetchResult(
            source_name=self.name,
            fetched_at=fetched_at,
            items=items,
            errors=[],
        )

    def _request(self, params: dict[str, Any]) -> Any:
        headers = {
            "User-Agent": "EventAlpha-MVP/0.1 (+https://github.com/gdelt/gdelt.github.io)",
            "Accept": "application/json",
        }
        try:
            return self.request_get(
                self.api_url,
                params=params,
                timeout=self.timeout,
                headers=headers,
            )
        except TypeError:
            return self.request_get(self.api_url, params=params, timeout=self.timeout)


def _parse_gdelt_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%dT%H%M%SZ"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _retry_after_seconds(response: Any) -> float | None:
    headers = getattr(response, "headers", {}) or {}
    value = headers.get("Retry-After") if hasattr(headers, "get") else None
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return None
