"""Base protocol for news providers."""

from __future__ import annotations

from typing import Protocol

from .schemas import NewsFetchResult


class NewsProvider(Protocol):
    """A provider that fetches candidate news without analyzing it."""

    name: str

    def fetch(self, query: str | None = None, limit: int = 20) -> NewsFetchResult:
        """Fetch candidate news items."""
        ...
