# EventAlpha-MVP

EventAlpha-MVP 是一个热点事件驱动的投资研究辅助多 Agent 系统。它不是荐股系统，不做自动交易，不输出买入、卖出、目标价，也不构成投资建议。

一句话介绍：EventAlpha-MVP 将热点新闻或公告转化为可追踪、可复盘、可纠错的事件研究卡片。

## 第一版 MVP 做什么

- 输入单条热点事件新闻或公告。
- 抽取结构化事件。
- 进行 mock 可信度评分和事件影响评分。
- 生成事件影响金融市场的因果链。
- 用反方检查过滤伪相关和过度推理。
- 映射到行业、指数、ETF 或主题方向。
- 生成合规事件卡片。
- 写入 Prediction Ledger。
- 创建 T+1、T+3、T+7 mock 复盘任务。
- 使用 mock market data 完成复盘。
- 区分方向正确和因果正确。
- 根据复盘结果生成规则权重更新记录。

## 第一版 MVP 不做什么

- 不接真实 LLM、GDELT、OpenBB、真实新闻源或 Web 服务。
- 不接 FastAPI、Streamlit 或复杂 Web 前端。
- 不自动抓取新闻。
- 不做微信推送、订阅系统或机构 API。
- 不做自动交易、调仓、下单或组合管理。
- 不输出买入、卖出、目标价、保证收益、杠杆建议或个股确定性结论。
- 不实现完整事件研究统计模型或大规模向量库。

## 系统闭环

```text
RawNews
-> StructuredEvent
-> EventVerification
-> ImpactScore
-> CausalChain
-> AntiSpuriousCheck
-> MarketMapping
-> EventCard
-> PredictionLedgerEntry
-> ReviewTask
-> ReviewResult
-> RuleUpdate
```

核心原则是：事件不是分析终点，而是可验证和可学习的起点。每次判断必须写入 Prediction Ledger，后续用市场表现进行复盘，再更新规则权重。

## 目录结构

```text
eventalpha/
  schemas/          Pydantic 数据结构
  agents/           规则驱动 mock Agent
  orchestration/    单事件分析 pipeline 和复盘 pipeline
  services/         账本、卡片、规则更新服务
  data_sources/     Mock、CSV、AkShare 和 ProviderRouter 行情接口
  repositories/     SQLite repository 和 schema.sql
  rules/            事件分类、资产映射、因果规则种子文件
  examples/         demo 输入事件
scripts/            CLI demo 脚本
tests/              基础测试
docs/               项目需求、范围、架构和合规文档
external_repos/     只作参考的外部项目
```

## 安装

```bash
pip install -r requirements.txt
```

## 运行 Demo

先运行单事件分析 demo：

```bash
python scripts/run_demo_event.py
```

再运行 mock 复盘 demo：

```bash
python scripts/run_mock_review.py
```

也可以使用本地 CSV 价格序列运行复盘 demo：

```bash
python scripts/run_csv_review.py
```

如已安装 AkShare 并允许联网，可以运行 AkShare 行情复盘：

```bash
python scripts/run_akshare_review.py
python scripts/run_akshare_review.py --asset 沪深300 --horizon T+3 --start-date 2024-06-18
python scripts/run_akshare_review.py --asset 沪深300 --horizon T+3 --no-proxy
python scripts/run_akshare_review.py --refresh-cache
```

对于已配置 `eastmoney_secid` 的指数资产，AkShareProvider 会优先直连 EastMoney 历史 K 线接口，绕过 AkShare 指数代码映射接口；如果 EastMoney 历史接口本身不可访问，仍会清晰报错。

检查资产代理映射覆盖率：

```bash
python scripts/check_asset_coverage.py
```

使用 ProviderRouter 自动选择 Mock、CSV 或 AkShare 复盘：

```bash
python scripts/run_router_review.py
python scripts/run_router_review.py --horizon T+3 --no-proxy
```

验证真实 provider route 连通性并生成报告：

```bash
python scripts/validate_provider_routes.py
python scripts/validate_provider_routes.py --refresh-cache --write-report
```

运行测试：

```bash
pytest
```

默认 SQLite 数据库会写入项目根目录的 `eventalpha_mvp.sqlite3`。如需修改位置，可以设置 `EVENTALPHA_DB_PATH`。

## 合规边界

系统可以输出：

- 可能受益；
- 可能承压；
- 关注方向；
- 风险因素；
- 验证指标；
- 市场观察信号。

系统不输出：

- 买入；
- 卖出；
- 目标价；
- 保证收益；
- 杠杆建议；
- 个股确定性结论；
- 自动交易指令。

所有事件卡片和复盘卡片必须包含：

> 本内容仅用于事件研究和市场分析，不构成投资建议。市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。

## Phase 3A LLM Structured Extraction

Phase 3A adds optional LLM structured output infrastructure. The default pipeline still uses deterministic mock agents. The LLM demo uses `MockLLMClient` by default and does not require an API key:

```bash
python scripts/run_llm_extraction_demo.py
```

To call a real OpenAI-compatible API, configure a local `.env` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`, then run:

```bash
python scripts/run_llm_extraction_demo.py --real-llm
python scripts/run_llm_extraction_demo.py --real-llm --base-url https://api.deepseek.com --model deepseek-chat
```

LLM traces are written to `data/llm_traces/` and are ignored by git. LLM output is always validated by Pydantic before business code can use it.

Run the full event pipeline with optional LLM extraction:

```bash
python scripts/run_llm_event_pipeline.py
python scripts/run_llm_event_pipeline.py --real-llm
python scripts/run_llm_event_pipeline.py --real-llm --failure-mode fallback
```

Evaluate and normalize LLM extraction quality before replacing more agents:

```bash
python scripts/evaluate_llm_extraction.py
python scripts/evaluate_llm_extraction.py --real-llm --write-report
```

Evaluate LLM extraction against the hand-written gold set and downstream consistency gates:

```bash
python scripts/evaluate_llm_extraction_gold.py
python scripts/evaluate_extraction_downstream.py
```

Phase 3B.7 adds entity keyword completion and gold-based downstream alert metrics:

- `missed_alert_count`: gold expects alert but calibrated LLM misses it.
- `over_alert_count`: calibrated LLM alerts when gold does not expect one.
- `gold_event_level_mismatch_count`: calibrated LLM level differs from gold.
- `gold_trigger_alert_mismatch_count`: calibrated LLM alert flag differs from gold.

Real DeepSeek/OpenAI-compatible recheck:

```bash
python scripts/evaluate_llm_extraction_gold.py --real-llm --calibrated --write-report
python scripts/evaluate_extraction_downstream.py --real-llm --calibrated --write-report
```

Run optional LLM causal reasoning without replacing the default pipeline:

```bash
python scripts/run_llm_causal_pipeline.py
python scripts/run_llm_causal_pipeline.py --real-llm --failure-mode fallback
python scripts/evaluate_llm_causal_reasoning.py
python scripts/evaluate_llm_causal_reasoning.py --real-llm --write-report
```

Run optional LLM anti-spurious critic without replacing the default pipeline:

```bash
python scripts/run_llm_anti_spurious_pipeline.py
python scripts/run_llm_anti_spurious_pipeline.py --real-llm --failure-mode fallback
python scripts/evaluate_llm_anti_spurious.py
python scripts/evaluate_llm_anti_spurious.py --real-llm --write-report
```

## Phase 3D.5 Anti-Spurious Calibration

Phase 3D.5 keeps the default rule-based pipeline unchanged, but makes the optional LLM anti-spurious critic more usable for downstream event cards and future news flow.

- Add LLM-only anti-spurious risk calibration so direct, credible, short-chain events can fall to `low` risk when they meet conservative downgrade criteria.
- Keep rumor, weak-verification, warning-heavy, second-order, and too-far-mapping cases from becoming overconfident.
- Compress anti-spurious `issues` and `required_verifications` to the most important 3-5 items.
- Compact EventCard `risk_factors` and `verification_indicators` so cards stay readable.
- Extend evaluation with calibration counts, post-compression counts, and EventCard-length metrics.

Offline defaults remain:

```bash
python scripts/run_demo_event.py
python scripts/run_llm_anti_spurious_pipeline.py
python scripts/evaluate_llm_anti_spurious.py
pytest
```

Manual real DeepSeek / OpenAI-compatible recheck:

```bash
python scripts/run_llm_anti_spurious_pipeline.py --real-llm --failure-mode fallback
python scripts/run_llm_anti_spurious_pipeline.py --real-llm --use-llm-extraction --use-llm-causal --failure-mode fallback
python scripts/evaluate_llm_anti_spurious.py --real-llm --write-report
```

See `docs/phase3d5_anti_spurious_calibration.md` for the detailed calibration rules, critique compression policy, EventCard compaction behavior, and evaluation metrics.

## Phase 4A News Source Collection

Phase 4A adds a lightweight news-discovery layer that normalizes mock, GDELT, and RSS items into `NewsItem`, then deduplicates, keyword-filters, and optionally converts selected items into the existing `RawNews` pipeline. The default scout path is offline and uses deterministic mock news; real GDELT/RSS fetches require `--real-fetch`.

Run the offline scout:

```bash
python scripts/run_news_scout.py
python scripts/run_news_scout.py --analyze-top 1
```

Run real fetch manually:

```bash
python scripts/run_news_scout.py --real-fetch --query "AI chip export control" --limit 10
python scripts/run_news_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --limit 10
python scripts/run_news_scout.py --real-fetch --query "AI chip export control" --limit 10 --analyze-top 3 --use-llm-extraction --use-llm-causal --use-llm-anti-spurious --failure-mode fallback
```

Use `--source rss` to skip GDELT when the hosted API is rate-limited. Phase 4A does not add scheduling, UI, push notifications, historical news storage, trading, or ledger schema changes. See `docs/phase4a_news_source_collection.md` for provider behavior, dedup/filter rules, mock/real commands, and the non-investment-advice boundary.

## Phase 4B Event Clustering

Phase 4B clusters related `NewsItem` candidates into lightweight `EventCluster` objects, computes preliminary multi-source support, and can convert top clusters into `RawNews` for the existing EventAlpha pipeline. It does not use LLMs or vector databases for clustering and does not change ledger schema.

Run the offline cluster scout:

```bash
python scripts/run_event_cluster_scout.py
python scripts/run_event_cluster_scout.py --analyze-top 1
```

Run real RSS-only clustering when GDELT is rate-limited:

```bash
python scripts/run_event_cluster_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10
python scripts/run_event_cluster_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10 --analyze-top 3 --use-llm-extraction --use-llm-causal --use-llm-anti-spurious --failure-mode fallback
```

See `docs/phase4b_event_clustering_verification.md` for clustering rules, verification status meanings, cluster-to-RawNews conversion, and the boundary between source support and final truth verification.

## Phase 4C Multi-source Credibility

Phase 4C adds rule-based cluster-level credibility reports on top of `EventCluster`. It classifies source credibility, extracts lightweight claims, checks claim consistency, detects official evidence signals, and can pass the report into `RawNews.metadata` without changing ledger schema.

Run offline credibility checks:

```bash
python scripts/run_cluster_credibility.py
python scripts/run_event_cluster_scout.py --with-credibility
python scripts/run_event_cluster_scout.py --analyze-top 1 --with-credibility
```

Run real RSS credibility checks:

```bash
python scripts/run_cluster_credibility.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10
```

With optional downstream LLM analysis:

```bash
python scripts/run_event_cluster_scout.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10 --with-credibility --analyze-top 3 --use-llm-extraction --use-llm-causal --use-llm-anti-spurious --failure-mode fallback
```

See `docs/phase4c_multi_source_credibility.md` for source credibility rules, claim extraction, claim consistency, official evidence heuristics, and the boundary between pre-verification and final truth verification.

## Phase 4D Event Lifecycle Tracking

Phase 4D tracks event lifecycle state across scout runs. It matches new clusters to existing tracked events, records timeline updates, detects source-count increases, credibility upgrades, official evidence, uncertainty, conflicts, stale events, and closed events. The store is a local JSON file and does not change ledger schema.

Run offline lifecycle tracking:

```bash
python scripts/run_event_lifecycle_tracker.py --reset-store
python scripts/run_event_lifecycle_tracker.py
python scripts/run_event_lifecycle_tracker.py --list-active
```

Run real RSS lifecycle tracking:

```bash
python scripts/run_event_lifecycle_tracker.py --real-fetch --source rss --rss-feed "https://news.google.com/rss/search?q=AI%20chip%20export%20control&hl=en-US&gl=US&ceid=US:en" --query "AI chip export control" --limit 10
```

Optional local pipeline analysis for updated events:

```bash
python scripts/run_event_lifecycle_tracker.py --analyze-updated 1
```

See `docs/phase4d_event_lifecycle_tracking.md` for lifecycle stages, matching rules, JSON store behavior, mock/real commands, and the non-investment-advice boundary.

## Phase 5A Historical Case Store

Phase 5A adds an offline historical case store for comparing current events with illustrative past cases. It includes schemas, seed demo cases, a JSON store, rule-based search, and a report script. It does not use RAG, embeddings, LLMs, scheduling, UI, or ledger schema changes.

Run the historical case demo:

```bash
python scripts/run_historical_case_demo.py
python scripts/run_historical_case_demo.py --seed
python scripts/run_historical_case_demo.py --query "AI chip export control"
python scripts/run_historical_case_demo.py --event-type ai_export_control
```

Seed outcomes are MVP illustrative examples, not verified market returns or investment advice. See `docs/phase5a_historical_case_store.md` for schema details, store/search behavior, current-event helper usage, and future Phase 5B/5C expansion paths.

## Phase 5B Historical Analogy Retrieval

Phase 5B explains historical analogies on top of the Phase 5A case store. It scores event type, assets, entities, industries, tags, causal-chain terms, query keywords, and region, then explains similarities, differences, transferable lessons, non-transferable lessons, verification suggestions, and risk notes. It remains offline and does not use LLMs, RAG, embeddings, or ledger schema changes.

Run the historical analogy demo:

```bash
python scripts/run_historical_analogy_demo.py
python scripts/run_historical_analogy_demo.py --query "AI chip export control"
python scripts/run_historical_analogy_demo.py --event-type ai_export_control
python scripts/run_historical_analogy_demo.py --asset "AI chips"
python scripts/run_historical_analogy_demo.py --demo-current-ai-export
python scripts/run_historical_analogy_demo.py --from-active-event 1
```

Historical analogies are research aids only; seed outcomes are illustrative examples, not verified market returns. Phase 5B.1 adds strength labels, input-context diagnostics, low-score explanations, and event-family-specific verification suggestions. See `docs/phase5b_historical_analogy_retrieval.md` and `docs/phase5b1_analogy_context_calibration.md` for scoring dimensions, explanation behavior, demo usage, and future Phase 5C expansion.

## Phase 5C Historical Outcome Comparison

Phase 5C compares historical case outcome windows with current review or market-return results. It is a deterministic offline helper, not a full event study, and it keeps `manual_seed_demo` outcomes clearly marked as illustrative examples rather than verified backtests. Phase 5C.1 adds non-zero manual seed demo returns, deterministic mock current-outcome scenarios, and comparison data-quality/reliability labels.

Run the historical outcome comparison demo:

```bash
python scripts/run_historical_outcome_comparison_demo.py
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome --mock-outcome-scenario aligned
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome --mock-outcome-scenario mixed
python scripts/run_historical_outcome_comparison_demo.py --demo-current-ai-export --with-mock-current-outcome --mock-outcome-scenario opposite
```

Mock outcomes are deterministic demo data, not real market data. See `docs/phase5c_historical_outcome_comparison.md` for schemas, comparison statuses, data-quality/reliability labels, mock current outcome usage, ReviewResult wiring, and future real ReviewResult/MarketReturn integration.

## 后续路线

1. 用真实 LLM 替换 mock Agent，但保持 schema 和 pipeline 接口稳定。
2. 接入真实新闻源和公告源，加入去重、聚类和可信度验证。
3. 扩展 AkShare、OpenBB 或其他行情数据源映射，逐步替换 mock market data。
4. 扩展历史相似事件库和因果规则库。
5. 增加 FastAPI 和前端事件控制台。
6. 增加更完整的事件研究和异常收益统计。
