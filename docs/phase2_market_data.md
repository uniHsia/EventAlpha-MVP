# Phase 2 Market Data

Phase 2A 先实现 `CSVMarketDataProvider`，目的是把复盘层从“直接读取 mock return”升级为“通过统一 provider 接口获取行情收益”。这样后续接入 AkShare 时，只需要新增 provider，不需要重写 Prediction Ledger 或 review pipeline。

## CSV 格式

CSV 文件使用 UTF-8 编码，字段固定为：

```csv
date,asset_name,close
2026-06-18,国产 AI 芯片,100
2026-06-19,国产 AI 芯片,103
2026-06-23,国产 AI 芯片,108
```

- `date` 使用 `YYYY-MM-DD`。
- `asset_name` 使用系统内部资产名称。
- `close` 是收盘价或可比价格点，解析为 float。

## T+N 规则

- `T+1` 表示起始日期之后第 1 个可用交易日。
- `T+3` 表示起始日期之后第 3 个可用交易日。
- `T+7` 表示起始日期之后第 7 个可用交易日。
- 如果起始日期不是交易日，使用起始日期之后第一个可用价格点作为 start price。
- 收益率计算为 `end_close / start_close - 1`。
- Phase 2A 不接真实交易日历，不按自然日直接加天数。

## 后续 AkShare 接入

Phase 2B 可以新增 `AKShareMarketDataProvider`，实现与 CSVProvider 相同的接口：

```text
get_price_series(asset_name, start_date, end_date)
get_asset_return(asset_name, horizon, start_date=None)
get_benchmark_return(benchmark, horizon, start_date=None)
```

`eventalpha/rules/asset_code_mapping.yaml` 当前只保存 demo symbol，后续可把 `provider_symbol` 替换为真实指数、ETF 或主题代理代码。

## 合规提示

CSV demo 数据是人工构造的价格序列，仅用于验证复盘接口和工程闭环。本内容仅用于事件研究和市场分析，不构成投资建议。
