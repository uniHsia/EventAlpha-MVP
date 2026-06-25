# EventAlpha Agent Capability Progress

## 当前已完成的核心闭环

EventAlpha 已形成本地可演示的事件研究闭环：新闻/事件输入生成 EventCard，Prediction Ledger 记录事件到资产的市场判断，ReviewResult 对到期预测做自动复盘，RuleUpdate 记录规则修正，Daily Briefing 汇总核心结果，Streamlit 控制台展示本地状态和 demo state。

所有展示内容均应区分真实本地落盘数据、Demo 数据与 placeholder，且不构成投资建议。

## 信息源覆盖能力

Source Coverage MVP 记录当前系统检查了哪些来源、哪些来源成功、哪些来源失败、哪些来源仍为待接入。默认离线模式只检查 Demo RawNews；RSS/GDELT 真实来源必须显式启用。官方源、专业财经媒体、行业源当前作为 placeholder 标注，不伪装成已接入。

运行：

```powershell
python scripts/run_source_coverage_report.py --demo-mode
```

## 搜索质量评估

Search Quality Report MVP 汇总本次扫描的 raw news 数量、去重后数量、候选聚类数量、EventCard 数量、高优先级事件数量、Prediction Ledger 数量、来源贡献和失败来源。demo mode 基于本地 demo state 和离线 mock registry 生成，报告中标注 `demo_mode=true`。

运行：

```powershell
python scripts/run_search_quality_report.py --demo-mode
```

## 因果证据层

Causal Evidence Layer MVP 为 EventCard 的因果链步骤标注 evidence type：`source`、`historical_case`、`market_data`、`assumption`、`missing`。它只使用本地 EventCard、HistoricalCase、ReviewResult 和 Prediction Ledger 数据。缺证据时明确标注 assumption 或 missing，并给出需要验证的指标。

## 复盘反馈信号

Rule Feedback MVP 从 ReviewResult 和 RuleUpdate 生成轻量校准信号。正向复盘可提升置信度，负向复盘可降低置信度，总调整限制在 `[-0.10, +0.10]`。本阶段只生成和展示信号，不写回 Prediction Ledger，不改变稳定 pipeline。

运行：

```powershell
python scripts/run_rule_feedback_report.py --demo-mode
```

## 订阅推送 MVP

订阅推送 MVP 使用本地 `data/subscribers.demo.json` 做订阅者配置，根据关键词、行业、资产、事件类型和优先级匹配 EventCard，生成 push outbox。微信通道当前为 `wechat_placeholder`，只完成订阅匹配和消息生成，未接入真实公众号或企业微信发送 API。

运行：

```powershell
python scripts/run_push_outbox_demo.py --demo-mode
```

## 当前仍未完成的生产级能力

- 真实微信公众号 / 企业微信 API 接入；
- 生产数据库和多用户数据隔离；
- 长期稳定调度服务和任务监控；
- 稳定实时行情源和多市场数据 provider；
- 用户登录、权限和订阅管理后台；
- 大规模历史案例库和可审计历史数据来源。
