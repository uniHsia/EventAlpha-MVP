# MVP 范围

第一版 MVP 目标是打通最小可运行闭环，而不是做完整生产系统。

## 第一版做

- 单条事件输入；
- 事件抽取；
- 可信度评分；
- 事件影响评分；
- 因果链生成；
- 伪相关过滤；
- 资产映射；
- 事件卡片生成；
- Prediction Ledger；
- T+1、T+3、T+7 mock 复盘；
- 规则权重更新；
- CLI Demo。

## 第一版不做

- 自动交易；
- 买卖建议；
- 目标价；
- 真实行情接入；
- 自动新闻爬虫；
- 微信推送；
- 订阅系统；
- 复杂 Web 前端；
- 大规模向量库；
- 完整事件研究统计模型。

## 验收标准

- `python scripts/run_demo_event.py` 能运行单事件分析并写入 Prediction Ledger。
- `python scripts/run_mock_review.py` 能读取预测账本并生成 mock T+3 复盘结果。
- `pytest` 能通过基础 pipeline 和 ledger service 测试。
- 所有事件卡片和复盘输出都包含合规风险提示。
