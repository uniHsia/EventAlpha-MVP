# Phase 4C Multi-source Credibility Verification

Phase 4C adds rule-based cluster-level pre-verification on top of Phase 4B `EventCluster`. It is stricter than Phase 4B source-count labels, but it is still not final fact-checking.

This phase does not use LLMs, crawl full web pages, change ledger schema, add UI, schedule jobs, or provide investment advice.

## Why Phase 4B Status Is Not Enough

Phase 4B `verification_status` tells us whether a cluster is single-source, multi-source, analysis-only, or unconfirmed. That is useful for collection triage, but it does not ask whether the sources are credible, whether the claims are consistent, or whether official evidence is present.

Phase 4C adds those pre-verification signals before a cluster becomes pipeline input.

## SourceCredibilityRegistry

`SourceCredibilityRegistry` classifies sources without network calls.

It recognizes:

- official institutions such as government, ministry, central bank, Federal Reserve, White House, Commerce Department, 商务部, 央行, 白宫
- mainstream or financial media such as Reuters, AP, BBC, NBC, UPI, Al Jazeera, Bloomberg, CNBC
- think-tank and analysis sources such as Brookings, Tech Policy Press, Foundation for American Innovation
- aggregators such as Google News
- unknown blogs or unclassified sources

Aggregators are explicitly not treated as original reporting sources.

## Claim Extraction

`ClusterClaimExtractor` extracts lightweight claims from cluster canonical title and member items. It does not use LLMs.

It detects:

- uncertainty markers: weighs, mulls, considering, reportedly, rumor, 尚未确认, 考虑, 拟, 传闻
- analysis/opinion markers: strategy, opinion, analysis, backfiring, missing piece, explains, why
- official announcement markers: announces, says, ministry, central bank, official, 商务部, 央行, 宣布
- market reaction markers: market, shares, stocks, prices, yields, oil, gold

Every cluster gets at least one claim.

## Claim Consistency

`ClaimConsistencyService` summarizes cross-source claim status:

- `consistent_multi_source`
- `single_source_claim`
- `analysis_only_claim`
- `unconfirmed_claim`
- `conflicting_claim`

Contradiction markers such as denies, rejects, false, 辟谣, 否认 force `conflicting_claim`.

## Official Evidence

`OfficialEvidenceHeuristic` checks only available cluster metadata:

- `official_source_present`
- `official_claim_reported_by_media`
- `no_official_evidence`

It does not crawl official pages or perform final fact verification.

## ClusterCredibilityReport

`ClusterCredibilityService` produces `ClusterCredibilityReport` with:

- source credibility summary
- extracted claims
- consistency status
- official evidence status
- credibility score and status
- risk flags
- verification notes

The score rewards high-credibility independent sources and official evidence. It penalizes single-source, analysis-only, uncertainty, aggregator-only, missing official evidence, and conflicting claims.

## Running Mock

```bash
python scripts/run_cluster_credibility.py
python scripts/run_event_cluster_scout.py --with-credibility
python scripts/run_event_cluster_scout.py --analyze-top 1 --with-credibility
```

## Running Real RSS

```bash
python scripts/run_cluster_credibility.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10
```

Optional downstream LLM analysis:

```bash
python scripts/run_event_cluster_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10 --with-credibility --analyze-top 3 --use-llm-extraction --use-llm-causal --use-llm-anti-spurious --failure-mode fallback
```

## Pipeline Connection

When `run_event_cluster_scout.py --with-credibility --analyze-top N` is used, the selected cluster credibility report is written into `RawNews.metadata`. Existing `RawNews`, EventVerification, ledger, and pipeline schemas remain unchanged.

## Boundary

Phase 4C is cluster-level pre-verification. It does not replace the existing EventVerification agent, does not provide final truth verification, and does not constitute investment advice.

EventAlpha is only for event research and market analysis. It does not provide buy/sell recommendations, target prices, guaranteed returns, or automated trading.
