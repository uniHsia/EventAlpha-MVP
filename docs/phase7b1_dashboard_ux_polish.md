# Phase 7B.1 Streamlit Console UX Polish

Phase 7B.1 turns the read-only Streamlit console from a developer-style data
viewer into a teacher-friendly EventAlpha research-agent demo. It does not add
backend capability, write ledger rows, call LLMs, fetch network data, start
scheduler daemons, or change schemas.

## Dashboard Meaning

- 紧急事件: events that would need high-frequency tracking.
- 高优先级: events that should be followed with enhanced attention.
- 普通跟踪: events kept under normal observation.
- 背景观察: analysis-only, commentary, or lower-priority items.
- 自动复盘状态: the latest auto-review scheduler run status.
- 复盘结果数: asset-level ReviewResult rows from the latest/local review data.
- 规则更新数: rule updates generated from review feedback.

## Top Events

Top Events exclude `background`, `ignore`, and `analysis_only` items. Remaining
urgent/high/normal events are sorted by urgency score and displayed with title,
stage, source, credibility, summary, reasons, and verification hints.

## Recent Reviews

Recent Reviews reuse Phase 7A.1 ReviewResult deduplication by prediction, asset,
and horizon. Each result is explained in Chinese:

- valid: 因果链获得支持.
- invalid: 当前市场表现未验证该判断.
- unknown: 观察方向或数据不足.
- mixed/watch: 仅记录市场表现.
- wrong asset mapping: 可能需要检查资产映射.

Returns are shown as signed percentages. Demo/mock data is explicitly labeled as
only for closed-loop demonstration.

## Rule Updates

Rule updates reuse rule/action aggregation and show count, latest old/new
weights, rationale, and Chinese action labels:

- strengthen: 强化规则.
- slightly_strengthen: 小幅强化规则.
- weaken: 削弱规则.
- keep/unchanged: 保持规则.

## Warning Handling

Dashboard warnings are friendly summaries. For example,
`RSS query matched no items` becomes:

> 数据源提示：RSS 最近多次未匹配到新闻，不影响本地 demo/mock 流程。

Raw warnings remain available inside expanders for debugging. Warning polish only
changes presentation and does not edit scheduler run logs.

## Read-Only Boundary

The console reads local reports, scheduler JSON/JSONL, lifecycle JSON, and
SQLite ledger rows in read-only mode. It does not write reports from the UI,
write ledger rows, trigger review jobs, start APScheduler, push notifications,
or output trading instructions.

本内容仅用于事件研究和市场分析，不构成投资建议。市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。
