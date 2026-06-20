"""Offline tests for GDELTProvider."""

from __future__ import annotations

from eventalpha.news import GDELTProvider


class _FakeResponse:
    def __init__(
        self,
        payload: dict,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> dict:
        return self.payload


class _BrokenJsonResponse:
    status_code = 200
    headers: dict[str, str] = {}

    def json(self) -> dict:
        raise ValueError("empty response")


def test_gdelt_provider_maps_mock_response_to_news_items() -> None:
    """Mock GDELT JSON should normalize to NewsItem without network."""
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return _FakeResponse(
            {
                "articles": [
                    {
                        "title": "Middle East oil supply disruption risk",
                        "url": "https://example.com/oil",
                        "domain": "example.com",
                        "sourceCountry": "AE",
                        "language": "English",
                        "seendate": "20240617103000",
                    }
                ]
            }
        )

    result = GDELTProvider(request_get=fake_get).fetch(query="oil supply", limit=3)

    assert calls[0][1]["query"] == "oil supply"
    assert calls[0][1]["maxrecords"] == 3
    assert not result.errors
    assert len(result.items) == 1
    assert result.items[0].title == "Middle East oil supply disruption risk"
    assert result.items[0].source == "example.com"
    assert result.items[0].country == "AE"
    assert result.items[0].published_at is not None


def test_gdelt_provider_records_network_error() -> None:
    """Provider errors should be returned in NewsFetchResult.errors."""
    def fake_get(url, params, timeout):
        raise RuntimeError("network unavailable")

    result = GDELTProvider(request_get=fake_get).fetch(query="tariff", limit=2)

    assert result.items == []
    assert result.errors
    assert "network unavailable" in result.errors[0]


def test_gdelt_provider_retries_rate_limit_and_respects_retry_after() -> None:
    """HTTP 429 should be retried before returning normalized results."""
    calls = []
    sleeps = []

    def fake_get(url, params, timeout, headers=None):
        calls.append((url, params, timeout, headers))
        if len(calls) == 1:
            return _FakeResponse({}, status_code=429, headers={"Retry-After": "0.25"})
        return _FakeResponse(
            {
                "articles": [
                    {
                        "title": "AI chip export control update",
                        "url": "https://example.com/ai",
                        "domain": "example.com",
                    }
                ]
            }
        )

    result = GDELTProvider(
        request_get=fake_get,
        max_retries=1,
        sleeper=sleeps.append,
    ).fetch(query="AI chip", limit=1)

    assert len(calls) == 2
    assert sleeps == [0.25]
    assert result.errors == []
    assert result.items[0].title == "AI chip export control update"
    assert calls[0][3]["Accept"] == "application/json"


def test_gdelt_provider_returns_actionable_rate_limit_error_after_retries() -> None:
    """Persistent HTTP 429 should produce a specific actionable error."""
    calls = []
    sleeps = []

    def fake_get(url, params, timeout, headers=None):
        calls.append((url, params, timeout, headers))
        return _FakeResponse({}, status_code=429)

    result = GDELTProvider(
        request_get=fake_get,
        max_retries=1,
        retry_backoff_seconds=0.5,
        sleeper=sleeps.append,
    ).fetch(query="AI chip", limit=1)

    assert len(calls) == 2
    assert sleeps == [0.5]
    assert result.items == []
    assert result.errors
    assert "GDELT rate limited request with status 429" in result.errors[0]
    assert "Retry later" in result.errors[0]


def test_gdelt_provider_retries_empty_or_non_json_response() -> None:
    """Transient empty responses should be retried and reported clearly."""
    calls = []
    sleeps = []

    def fake_get(url, params, timeout, headers=None):
        calls.append((url, params, timeout, headers))
        return _BrokenJsonResponse()

    result = GDELTProvider(
        request_get=fake_get,
        max_retries=1,
        retry_backoff_seconds=0.25,
        sleeper=sleeps.append,
    ).fetch(query="AI chip", limit=1)

    assert len(calls) == 2
    assert sleeps == [0.25]
    assert result.items == []
    assert "non-JSON or empty response" in result.errors[0]
    assert "retry later" in result.errors[0]
