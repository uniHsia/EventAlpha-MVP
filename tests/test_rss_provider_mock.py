"""Offline tests for RSSProvider."""

from __future__ import annotations

from eventalpha.news import RSSProvider


def test_rss_provider_parses_local_fixture(tmp_path) -> None:
    """RSSProvider should parse a local XML fixture without network access."""
    fixture = tmp_path / "feed.xml"
    fixture.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Fixture Finance Feed</title>
    <item>
      <title>AI chip export control expands</title>
      <description>Advanced GPU supply chain impact needs verification.</description>
      <link>https://example.com/ai-chip</link>
      <pubDate>Mon, 17 Jun 2024 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
""",
        encoding="utf-8",
    )
    provider = RSSProvider(
        feed_url=str(fixture),
        name="fixture_rss",
        language="en",
        country="US",
    )

    result = provider.fetch(limit=5)

    assert result.source_name == "fixture_rss"
    assert not result.errors
    assert len(result.items) == 1
    assert result.items[0].title == "AI chip export control expands"
    assert result.items[0].source == "Fixture Finance Feed"
    assert result.items[0].url == "https://example.com/ai-chip"
    assert result.items[0].published_at is not None


def test_rss_provider_query_filters_local_items(tmp_path) -> None:
    """Query filtering should happen after parsing and still stay offline."""
    fixture = tmp_path / "feed.xml"
    fixture.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Fixture Feed</title>
    <item><title>央行宣布降息</title><description>利率政策变化。</description></item>
    <item><title>Local sports update</title><description>Unrelated story.</description></item>
  </channel>
</rss>
""",
        encoding="utf-8",
    )

    result = RSSProvider(str(fixture), name="fixture").fetch(query="降息")

    assert [item.title for item in result.items] == ["央行宣布降息"]


def test_rss_provider_records_empty_result_when_query_terms_do_not_match(tmp_path) -> None:
    """RSS should avoid returning unrelated feed items when query terms do not match."""
    fixture = tmp_path / "feed.xml"
    fixture.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Fixture Feed</title>
    <item><title>AI chips policy update</title><description>Semiconductor story.</description></item>
  </channel>
</rss>
""",
        encoding="utf-8",
    )

    result = RSSProvider(str(fixture), name="fixture").fetch(query="unexpected narrow phrase")

    assert result.items == []
    assert result.errors == ["RSS query matched no items."]


def test_rss_provider_extracts_google_news_publisher_and_cleans_summary(tmp_path) -> None:
    """Google News RSS entries should expose publisher sources and clean HTML."""
    fixture = tmp_path / "google_news.xml"
    fixture.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>"AI chip export control" - Google News</title>
    <item>
      <title>AI chip export control update - Reuters</title>
      <description>&lt;a href="https://example.com"&gt;AI chip story&lt;/a&gt;&amp;nbsp;with details.</description>
    </item>
  </channel>
</rss>
""",
        encoding="utf-8",
    )

    result = RSSProvider(str(fixture), name="fixture").fetch(query="AI chip")

    assert result.items[0].source == "Reuters"
    assert result.items[0].summary == "AI chip story with details."
    assert "<a" not in result.items[0].raw_text
    assert "nbsp" not in result.items[0].raw_text


def test_rss_provider_missing_feedparser_records_error(monkeypatch) -> None:
    """Missing optional RSS dependency should not break non-RSS news paths."""
    from eventalpha.news import rss_provider

    def missing_feedparser():
        raise ImportError("No module named 'feedparser'")

    monkeypatch.setattr(rss_provider, "_load_feedparser", missing_feedparser)

    result = RSSProvider("https://example.com/feed.xml", name="fixture").fetch()

    assert result.items == []
    assert result.errors
    assert "feedparser" in result.errors[0]
