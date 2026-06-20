# Phase 4A News Source Collection & Event Discovery

Phase 4A moves EventAlpha from manually supplied demo `RawNews` toward a lightweight news-discovery layer. The scope is intentionally narrow: collect candidate news, normalize it to `NewsItem`, deduplicate, apply a loose keyword screen, and optionally convert selected items into the existing event pipeline.

This phase does not add scheduling, UI, push notifications, long-term news storage, trading, or ledger schema changes.

## Why Now

The Phase 3 LLM pipeline can extract, reason, critique, calibrate, and compress event cards. The next bottleneck is input discovery: the system needs a safe way to scout possible market-relevant news without forcing every downstream component to know source-specific formats.

Phase 4A adds that input layer while preserving the current rule-based default pipeline.

## Schemas

`NewsItem` is the normalized candidate-news schema. It carries:

- `news_id`: stable ID generated from URL when available, otherwise from normalized `source + title`.
- `title`, `summary`, `raw_text`: first-pass text fields; full article scraping is out of scope.
- `url`, `source`, `source_type`, `published_at`, `language`, `country`.
- `tags`: lightweight source/filter annotations.
- `fetched_at`: collection timestamp.

`NewsFetchResult` wraps one provider response:

- `source_name`: provider name.
- `items`: normalized `NewsItem` list.
- `errors`: non-fatal provider errors.
- `fetched_at`: provider fetch timestamp.

Provider errors are data, not process-level failures. One broken source should not crash the scout.

## GDELTProvider

`GDELTProvider` calls the GDELT DOC API:

```text
https://api.gdeltproject.org/api/v2/doc/doc
```

It sends `query`, `mode=ArtList`, `format=json`, and `maxrecords=limit`, then maps `articles` into `NewsItem`.

GDELT is useful for global event discovery, especially conflict, policy, trade, commodity, and supply-chain events. Its results still need later multi-source verification; Phase 4A only collects candidates.

## RSSProvider

`RSSProvider` uses `feedparser` to parse RSS or Atom feeds. It supports both local XML fixtures and real feed URLs. Tests use local fixtures only, so pytest does not require network access.

The provider maps title, summary/description, link, published time, source feed title, language, and country into `NewsItem`.

## Registry

`NewsSourceRegistry` coordinates multiple providers through `fetch_all(query, limit_per_source)`. It calls providers sequentially, aggregates items and errors, and catches single-provider exceptions.

Two builders are available:

- `build_mock_registry()`: deterministic offline items for tests and default script runs.
- `build_real_registry()`: GDELT plus optional RSS feeds; use only through `--real-fetch`.
- `build_real_registry(source="rss")`: RSS-only mode for cases where GDELT is rate-limited.
- `build_real_registry(source="gdelt")`: GDELT-only mode for focused provider checks.

## Dedup

`deduplicate_news()` applies simple deterministic deduplication:

- Prefer normalized URL when present.
- Fall back to normalized title when URL is missing.
- Keep the first item.
- Return before/after/duplicate counts.

Complex clustering and multi-source grouping are deferred to Phase 4B.

## Keyword Filter

`NewsKeywordFilter` is a loose candidate screen, not final event classification. It supports Chinese and English keywords for:

- conflict / Red Sea / Middle East
- rate policy / central banks / Federal Reserve
- tariffs / trade / export controls / sanctions
- earthquake / typhoon / flood / disasters
- AI chips / GPU / semiconductors / technology breakthroughs
- election / policy
- oil / gold / supply chain

Matched items receive filter reasons such as `technology`, `trade_policy`, or `conflict`.

## RawNews Conversion

`news_item_to_raw_news(item)` converts a `NewsItem` into the existing `RawNews` schema without changing it:

- `title`, `source`, `source_type`, `published_at`, `language`, and `url` are preserved.
- `raw_text` uses `raw_text`, then `summary`, then `title`.
- `news_id`, `url`, `country`, `tags`, and `fetched_at` are stored in `RawNews.metadata`.

## Running Mock Scout

Default runs are offline:

```bash
python scripts/run_news_scout.py
python scripts/run_news_scout.py --query "AI chip export control" --limit 10
python scripts/run_news_scout.py --analyze-top 1
```

`--analyze-top N` converts the top N filtered candidates into `RawNews` and calls the existing event pipeline with `persist=False`.

## Running Real Fetch

Real network calls are opt-in:

```bash
python scripts/run_news_scout.py --real-fetch --query "AI chip export control" --limit 10
python scripts/run_news_scout.py --real-fetch --query "tariff trade policy" --limit 10
python scripts/run_news_scout.py --real-fetch --query "Middle East oil supply" --limit 10
```

If GDELT returns `429`, skip it and run a query-specific RSS feed:

```bash
python scripts/run_news_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --limit 10
```

Optional LLM analysis can be enabled manually:

```bash
python scripts/run_news_scout.py --real-fetch --query "AI chip export control" --limit 10 --analyze-top 3 --use-llm-extraction --use-llm-causal --use-llm-anti-spurious --failure-mode fallback
```

## Why Pytest Stays Offline

Default tests use mock providers, local RSS XML fixtures, and injected mock GDELT responses. This keeps CI deterministic, avoids source-rate limits, and prevents network availability from changing test outcomes.

## Risk Boundary

EventAlpha is only for event research and market analysis. It does not provide investment advice, trading instructions, buy/sell recommendations, target prices, guaranteed returns, or automated trading.
