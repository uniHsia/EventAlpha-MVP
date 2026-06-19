# Phase 2B AkShare Provider

AkShareProvider 的目标是在不改动 Prediction Ledger 和 review pipeline 主流程的前提下，为复盘层提供真实行情数据。它实现与 MockProvider、CSVProvider 相同的 `MarketDataProvider` 接口，最终输出统一的 `PriceSeries`。

## 支持的 provider_type

第一版只实现少数稳定类型：

- `index`：A 股指数历史行情。若 mapping 中配置了 `eastmoney_secid`，优先直连 EastMoney 历史 K 线接口；否则调用 `ak.index_zh_a_hist`。
- `stock`：A 股个股历史行情，调用 `ak.stock_zh_a_hist`。
- `fund`：ETF / 基金历史行情，调用 `ak.fund_etf_hist_em`。

暂不支持 `concept` 概念板块。概念板块接口和名称稳定性后续在 Phase 2C 再处理。

## asset_code_mapping.yaml 写法

```yaml
沪深300:
  provider: akshare
  provider_type: index
  provider_symbol: "000300"
  eastmoney_secid: "1.000300"
  asset_type: benchmark
  name: 沪深300

中证军工:
  provider: akshare
  provider_type: index
  provider_symbol: "399967"
  eastmoney_secid: "0.399967"
  asset_type: index
  benchmark: 沪深300
```

当前主题资产如“国产 AI 芯片”仍保留 `provider: csv`，避免用不稳定或不明确的真实资产代理强行替代主题方向。

## EastMoney Direct Fallback

AkShare 的 `index_zh_a_hist` 在请求指数历史行情前，会先访问 EastMoney 的指数代码映射接口。如果该前置接口不可用，已知指数也会失败。

为提高稳定性，mapping 可以配置 `eastmoney_secid`。配置后 Provider 会优先请求：

```text
https://push2his.eastmoney.com/api/qt/stock/kline/get
```

并把返回的 `data.klines` 解析成统一的 `PriceSeries`。这条路径可以绕过 AkShare 的前置代码映射接口，但仍然依赖 EastMoney 历史 K 线接口可访问。

如果本机代理或 TUN 模式导致 EastMoney 请求被代理中断，可以在脚本中使用：

```bash
python scripts/run_akshare_review.py --asset 沪深300 --horizon T+3 --no-proxy
```

`--no-proxy` 只影响 Provider 自己的 EastMoney direct 请求；如果某个资产没有配置 `eastmoney_secid`，仍会走 AkShare 原接口。

## 缓存机制

缓存目录：

```text
data/cache/market_data/akshare/
```

缓存文件使用统一 CSV 格式：

```csv
date,asset_name,close
2024-01-02,沪深300,3290.12
```

规则：

- `use_cache=True` 且缓存存在时优先读缓存；
- `refresh_cache=True` 时忽略缓存并重新请求；
- 请求成功后写入缓存；
- 缓存目录已加入 `.gitignore`。

## 测试策略

默认测试不联网。AkShareProvider 的 mapping、DataFrame 标准化、缓存和 review pipeline 都用人工 DataFrame 或 monkeypatch 覆盖。

可选 live 测试只有在设置环境变量后才运行：

```bash
EVENTALPHA_RUN_LIVE_AKSHARE=1 pytest tests/integration/test_akshare_live.py
```

## 当前限制

- AkShare 接口可能受网络、数据源、字段变动影响。
- 当前只支持 index、stock、fund。
- 起始日期和 T+N 收益仍沿用 Phase 2A 的“可用交易日近似”规则。
- 主题资产仍需后续建立真实 ETF、指数或组合代理映射。

## 风险提示

本内容仅用于事件研究和市场分析，不构成投资建议。市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。
