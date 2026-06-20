# Phase 4D Event Lifecycle Tracking

Phase 4D adds a lightweight lifecycle layer after Phase 4A-4C news collection, clustering, and credibility pre-verification. It tracks whether an `EventCluster` is a new event, an update to an existing event, an upgrade, an official confirmation, an uncertainty signal, a conflict, or a stale/closed event.

This layer is only for event research and market analysis. It does not provide investment advice, does not make trading decisions, and does not change the ledger schema.

## TrackedEvent vs EventCluster

`EventCluster` is a snapshot from one scout run. It groups related `NewsItem` objects and carries cluster-level verification and credibility signals.

`TrackedEvent` is persistent lifecycle state across scout runs. It stores the canonical title, current summary, lifecycle stage, cluster IDs, sources, latest claims, dominant keywords, and timeline entries.

## Matching Logic

`EventLifecycleMatcher` matches a new cluster to existing tracked events with deterministic rules:

- Exact `cluster_id` match always matches.
- Otherwise it compares canonical title keywords, dominant keywords, and extracted claim text with Jaccard overlap.
- The default threshold is `0.42`.
- Title and claim overlap carry more weight than generic keyword overlap.
- Old events receive a time-distance penalty after 14 days and a stronger penalty after 45 days.
- `analysis_only` clusters do not easily merge into factual events unless the match is extremely strong.

No LLM, vector database, or web crawling is used.

## Lifecycle Stages

The first version uses string stages:

- `new`: newly discovered event.
- `developing`: previously seen event with updates but not yet confirmed.
- `confirmed`: high-confidence event with stronger credibility signals.
- `unconfirmed_or_considering`: proposal, rumor-like, weighs/mulls/considering type event.
- `analysis_only`: mostly commentary, think-tank, opinion, or analysis content.
- `conflicting`: contradictory claims were detected.
- `stale`: active event has not updated for the stale threshold.
- `resolved`: reserved for future manual or rule-based resolution.
- `closed`: stale event is no longer active.

## Update Types

Lifecycle updates are recorded as timeline entries and structured `EventLifecycleUpdate` objects:

- `new_event`
- `matched_existing`
- `source_count_increased`
- `credibility_upgraded`
- `official_evidence_added`
- `uncertainty_detected`
- `conflict_detected`
- `analysis_only_detected`
- `event_stale`
- `event_closed`

## JSON Store

The first store is a small JSON file at:

```bash
data/event_lifecycle_store.json
```

The file is ignored by git. Tests use temporary paths. The store supports load, save, reset, upsert, get-by-ID, list all events, and list active events.

## Mock Usage

Default commands are fully offline:

```bash
python scripts/run_event_lifecycle_tracker.py --reset-store
python scripts/run_event_lifecycle_tracker.py
python scripts/run_event_lifecycle_tracker.py --list-active
```

Optional local pipeline analysis for updated events:

```bash
python scripts/run_event_lifecycle_tracker.py --analyze-updated 1
```

This uses the existing rule-based EventAlpha pipeline with `persist=False`.

## Real RSS Usage

Real network fetch is opt-in:

```bash
python scripts/run_event_lifecycle_tracker.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10
```

Run the same command again after a few minutes to inspect whether events match existing tracked events, whether source counts change, and whether timeline entries are appended.

## Why No Scheduler Yet

Phase 4D intentionally avoids APScheduler, UI, push notifications, long-term historical case storage, and automatic trading. It only creates the lifecycle state and command-line workflow needed before scheduled automation is introduced.

## Risk Notice

EventAlpha is for event research and market analysis only. It does not provide investment advice. Market prices may already reflect relevant information, and any investment decision requires independent risk assessment.
