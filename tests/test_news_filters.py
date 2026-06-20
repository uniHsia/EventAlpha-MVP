"""Tests for news keyword filters."""

from __future__ import annotations

from eventalpha.news import NewsItem, NewsKeywordFilter


def _item(title: str, summary: str = "") -> NewsItem:
    return NewsItem(title=title, summary=summary, source="Mock")


def test_news_keyword_filter_matches_core_event_types() -> None:
    """Loose keyword filter should keep major event-discovery themes."""
    items = [
        _item("AI chip GPU export control expands"),
        _item("美国宣布新一轮关税政策"),
        _item("日本发生地震"),
        _item("Federal Reserve signals rate cut"),
        _item("Middle East conflict affects oil logistics"),
    ]

    result = NewsKeywordFilter().filter_items(items)

    assert result.after_count == 5
    reasons = [reason for item in items for reason in result.reasons[item.news_id]]
    assert "technology" in reasons
    assert "trade_policy" in reasons
    assert "natural_disaster" in reasons
    assert "rate_policy" in reasons
    assert "conflict" in reasons


def test_news_keyword_filter_rejects_unrelated_news() -> None:
    """Unrelated lifestyle news should be filtered out."""
    unrelated = _item("Local restaurant launches summer menu", "Community lifestyle update.")

    result = NewsKeywordFilter().filter_items([unrelated])

    assert result.candidates == []
    assert result.rejected == [unrelated]


def test_news_keyword_filter_does_not_match_english_keyword_inside_word() -> None:
    """The conflict keyword 'war' should not match unrelated words like warning."""
    warning = _item("Warning over fragile public finances", "Borrowing rises again.")

    result = NewsKeywordFilter().filter_items([warning])

    assert result.candidates == []
