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

- 不接真实 LLM。
- 不接 AkShare、GDELT、OpenBB 或其他真实外部数据源。
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
  data_sources/     mock market data provider
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

## 后续路线

1. 用真实 LLM 替换 mock Agent，但保持 schema 和 pipeline 接口稳定。
2. 接入真实新闻源和公告源，加入去重、聚类和可信度验证。
3. 接入 AkShare、OpenBB 或其他行情数据源，替换 mock market data。
4. 扩展历史相似事件库和因果规则库。
5. 增加 FastAPI 和前端事件控制台。
6. 增加更完整的事件研究和异常收益统计。
