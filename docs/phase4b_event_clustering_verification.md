# Phase 4B Event Clustering & Multi-source Verification

Phase 4B turns Phase 4A candidate `NewsItem` lists into lightweight `EventCluster` candidates. It is still a collection-layer feature: no scheduler, UI, push system, long-term news database, ledger schema change, trading, or investment advice.

## Why Cluster After Phase 4A

Phase 4A can collect and normalize news, but a real news flow often contains several articles about the same event. Clustering reduces duplicate cards, makes source support visible, and gives downstream EventAlpha analysis a cleaner event-level input.

## NewsItem vs EventCluster

`NewsItem` is one article or feed entry. `EventCluster` is a candidate event assembled from related `NewsItem` objects.

An `EventCluster` stores:

- a stable `cluster_id`
- `canonical_title` and optional `canonical_summary`
- the member `items`
- source statistics
- first/last seen timestamps
- dominant keywords and candidate event type
- preliminary `verification_status`
- collection-layer confidence
- debug reasons for clustering

## Clustering Logic

The first version intentionally avoids LLMs, vector databases, and external services.

`NewsClusterer` uses:

- normalized URL equality as a forced match
- title/summary keyword extraction
- English stopword filtering and word-boundary matching
- known Chinese/topic keywords from Phase 4A filter groups
- Jaccard keyword overlap with a configurable threshold
- greedy assignment into existing clusters

Canonical title selection favors the most informative title. Google News RSS publisher suffixes are weakened for keyword extraction, but original titles remain in cluster items.

## Multi-source Support

`ClusterVerificationService` computes a preliminary source-support label:

- `multi_source_supported`: at least 3 sources and at least 2 mainstream sources
- `multi_source_observed`: at least 2 sources
- `single_source`: exactly 1 source
- `analysis_only`: all sources look like commentary, think-tank, blog, or research-style sources
- `unconfirmed_or_considering`: title/summary contains rumor, reportedly, considering, weighs, mulls, 据称, 考虑, 拟, or 传闻

This is not final truth verification. It only summarizes collection-layer support before later credibility work.

## Cluster To RawNews

`event_cluster_to_raw_news(cluster)` converts a cluster into the existing `RawNews` schema without schema changes:

- `canonical_title` becomes the raw title
- summary text uses `canonical_summary` or the first few member summaries
- `source` is a compact source list
- `source_type` is inferred from cluster support/source types
- metadata stores `cluster_id`, `source_count`, `verification_status`, `confidence`, URLs, item IDs, and dominant keywords

## Mock Runs

Default runs are offline:

```bash
python scripts/run_event_cluster_scout.py
python scripts/run_event_cluster_scout.py --analyze-top 1
```

## Real RSS Runs

Real network is opt-in. When GDELT is rate-limited, use RSS-only:

```bash
python scripts/run_event_cluster_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10
```

Optional LLM downstream analysis:

```bash
python scripts/run_event_cluster_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10 --analyze-top 3 --use-llm-extraction --use-llm-causal --use-llm-anti-spurious --failure-mode fallback
```

## Boundary

Cluster verification is a source-support summary, not final fact-checking or truth verification. Phase 4C should add deeper multi-source credibility verification.

EventAlpha is only for event research and market analysis. It does not provide investment advice, trading instructions, buy/sell recommendations, target prices, guaranteed returns, or automated trading.
