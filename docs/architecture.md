# 系统架构

第一版 MVP 采用线性 pipeline，后续可替换为 LangGraph 或事件总线。

```text
Input Layer
-> Event Extraction Layer
-> Verification Layer
-> Scoring Layer
-> Causal Reasoning Layer
-> Anti-Spurious Check Layer
-> Market Mapping Layer
-> Card Generation Layer
-> Prediction Ledger Layer
-> Review Layer
-> Rule Update Layer
```

## Input Layer

- 输入：单条新闻或公告文本、来源、发布时间。
- 输出：`RawNews`。
- 职责：保留原始文本和来源元数据，作为后续可审计依据。

## Event Extraction Layer

- 输入：`RawNews`。
- 输出：`StructuredEvent`。
- 职责：抽取事件标题、类型、主体、地点、时间、状态、影响行业和资产提示。

## Verification Layer

- 输入：`RawNews`、`StructuredEvent`。
- 输出：`EventVerification`。
- 职责：根据来源类型、权威关键词、多源确认和语言风险生成可信度评分。

## Scoring Layer

- 输入：`StructuredEvent`、`EventVerification`。
- 输出：`ImpactScore`。
- 职责：计算事件影响分、事件等级、是否需要提醒和跟踪模式。

## Causal Reasoning Layer

- 输入：`StructuredEvent`、`ImpactScore`。
- 输出：`CausalChain`。
- 职责：生成“事件 -> 变量 -> 行业/主题 -> 资产方向”的因果链。

## Anti-Spurious Check Layer

- 输入：`CausalChain`、`MarketMapping` 前的事件上下文。
- 输出：`AntiSpuriousCheck`。
- 职责：检查链条是否过长、证据是否不足、映射是否二阶或过度外推。

## Market Mapping Layer

- 输入：`StructuredEvent`、`CausalChain`。
- 输出：`MarketMapping`。
- 职责：从规则文件映射到行业、指数、ETF 或主题方向，不生成买卖建议。

## Card Generation Layer

- 输入：前面所有结构化结果。
- 输出：`EventCard`。
- 职责：生成可读事件卡片，必须包含风险提示和后续验证指标。

## Prediction Ledger Layer

- 输入：`EventCard`、`MarketMapping`、`CausalChain`。
- 输出：`PredictionLedgerEntry`、`ReviewTask`。
- 职责：将结构化判断写入账本，创建 T+1/T+3/T+7 复盘任务。

## Review Layer

- 输入：`PredictionLedgerEntry`、mock market data。
- 输出：`ReviewResult`、`PredictionReviewSummary`。
- 职责：逐资产计算资产收益、基准收益、超额收益，再汇总整条预测，区分方向正确和因果正确。

## Rule Update Layer

- 输入：`PredictionReviewSummary`、原始规则。
- 输出：`RuleUpdate`。
- 职责：根据复盘结论更新规则权重，记录错误归因。

## Phase 1.5 Audit Additions

- Prediction Ledger 保存 `asset_confidence`、`chain_confidence`、`anti_spurious_adjusted_confidence` 和 `final_confidence`。
- 当前 mock 规则固定为：`final_confidence = round(asset_confidence * anti_spurious_adjusted_confidence, 4)`。
- `confidence` 字段暂时保留为兼容别名，内部以 `final_confidence` 作为最终置信度。
- 复盘层对同一预测中的所有 matching horizon 资产逐一生成 `ReviewResult`，再生成整条预测的 `PredictionReviewSummary`。
- `mixed/watch` 方向只进入观察统计，不计入方向正确或错误。
