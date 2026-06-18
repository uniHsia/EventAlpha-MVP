# 外部参考项目说明

`external_repos` 中的项目仅作为设计参考，不直接复制代码到主项目。

## TradingAgents

可借鉴：

- LangGraph 多 Agent 编排；
- 分析师、研究员、风险辩论的角色分工；
- 结构化输出 schema；
- 持久化 decision log 和 reflection。

不应照搬：

- Trader、Portfolio Manager、交易执行；
- BUY/SELL、目标价、仓位建议；
- 面向交易决策的终端定位。

## FinRobot

可借鉴：

- 金融工具注册方式；
- 数据源适配层；
- 新闻整合与报告分段生成；
- FastAPI/Web 应用组织方式。

不应照搬：

- 个股估值、DCF、target price；
- 投资评级和荐股式 equity research；
- 复杂报告生成流程。

## FinMem-LLM-StockTrading

可借鉴：

- 分层记忆；
- 重要性、时效性和反馈更新；
- 复盘后沉淀经验的思想。

不应照搬：

- 买卖决策；
- 组合和持仓管理；
- 自动交易目标。

## OpenBB

可借鉴：

- provider/extension 数据平台架构；
- 统一数据接口；
- API 和 MCP 暴露金融数据的思路。

不应照搬：

- 第一版不引入完整 OpenBB；
- 不将 MVP 做成大型数据平台。

## akshare

可借鉴：

- A 股、指数、ETF、宏观、商品和新闻数据接口；
- 国内市场数据覆盖。

不应照搬：

- 第一版不直接接入真实 AkShare；
- 不依赖不稳定实时数据完成 MVP 闭环。

## easy-event-study

可借鉴：

- 事件窗口；
- 异常收益和累计异常收益；
- CAPM、Fama-French、Market Adjusted Model 等事件研究方法。

不应照搬：

- 第一版不实现完整统计模型；
- 先用简单超额收益验证闭环。

## eventstudy

可借鉴：

- 单事件和多事件事件研究 API 思路；
- 复盘阶段统计验证的长期方向。

不应照搬：

- 第一版不做复杂事件研究包集成；
- 不让统计模型阻塞最小闭环。
