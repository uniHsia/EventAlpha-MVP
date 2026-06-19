# Phase 2C Asset Mapping and ProviderRouter

## 为什么需要资产代理映射层

事件 pipeline 输出的是研究方向，例如“国产 AI 芯片”“服务器”“供应链替代主题”。这些名称不一定是可直接复盘的真实行情标的。资产代理映射层把预测资产与可复盘代理资产分开，避免系统把不确定映射当成事实。

## 三个名称的区别

- `asset_name`：Prediction Ledger 中记录的资产或主题名称。
- `proxy_asset_name`：实际传给行情 provider 复盘的资产名称。
- `provider_symbol`：provider 可识别的代码或本地 CSV 名称。

示例：

```yaml
asset_name: 军工
proxy_asset_name: 中证军工
provider: akshare
provider_symbol: "399967"
```

## mapping_status

- `verified`：已经配置并可被 provider 识别的真实代理资产，例如沪深300、中证军工。
- `candidate`：MVP 可用于复盘的候选代理，多数是 CSV demo 资产。
- `unverified`：逻辑上可能相关，但尚未验证真实代理，默认不启用。
- `missing`：缺少可复盘映射，只能在 coverage report 中暴露。

## ProviderRouter 路由逻辑

ProviderRouter 实现与 MockProvider、CSVProvider、AkShareProvider 相同的 MarketDataProvider 接口。

路由顺序：

1. 优先查 `event_asset_proxy_mapping.yaml` 中的 event-specific mapping。
2. 如果没有命中，再 fallback 到 `asset_code_mapping.yaml`。
3. `verified` 优先于 `candidate`，`candidate` 优先于 `unverified`，最后是 `missing`。
4. 默认允许 `verified` 和 `candidate`；`unverified` 需要显式传入 `--allow-unverified`。
5. `missing` 和 `manual` 不会被执行，不会静默返回 0。

Benchmark 会优先使用当前资产相同 provider。例如 CSV 资产会优先用 CSV 中的“沪深300”作为基准，避免因 AkShare 网络失败影响 CSV 复盘。

## Coverage Report

运行：

```bash
python scripts/check_asset_coverage.py
```

该脚本不联网，只检查 demo events 和 proxy mapping，输出每个 event_type 下资产的 provider、proxy asset、mapping_status 和 summary。

## Router Review

运行：

```bash
python scripts/run_router_review.py
python scripts/run_router_review.py --horizon T+3 --no-proxy
python scripts/run_router_review.py --allow-unverified
```

Router review 会逐资产复盘。某个 AkShare 资产联网失败时，只记录该资产失败原因，其他 CSV/mock 资产继续复盘。

## 当前已验证资产

- 沪深300：AkShare index `000300`，EastMoney `1.000300`。
- 中证军工：AkShare index `399967`，EastMoney `0.399967`。
- 中证新能源汽车：AkShare index `399976`，EastMoney `0.399976`。

## 当前缺失或未验证映射

- 航空：缺少稳定代理，标记为 `missing`。
- 日本半导体材料：逻辑可能相关，但真实代理尚未验证，标记为 `unverified`。
- 原油、黄金等商品当前仍使用 CSV candidate，后续可接入 yfinance、OpenBB 或期货数据源。

## 后续扩展

后续新增 yfinance 或 OpenBB 时，只需要：

1. 新增 provider 实现 MarketDataProvider；
2. 扩展 `provider` Literal 和 ProviderRouter 分发；
3. 在 `event_asset_proxy_mapping.yaml` 中配置对应 provider 和 symbol。

本内容仅用于事件研究和市场分析，不构成投资建议。市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。
