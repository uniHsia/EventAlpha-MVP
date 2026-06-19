# Phase 2D Live Provider Validation

## 为什么需要 live provider validation

资产代理映射分两层可信度：一层是“这个代理资产在逻辑上是否适合作为事件复盘对象”，另一层是“provider 当前是否真的能拉到行情数据”。Phase 2D 引入 live validation，用来把这两件事分开记录，避免把无法拉数的真实代理误当成可复盘资产。

## mapping_status 与 validation_status

- `mapping_status`：映射逻辑可信度。
  - `verified`：真实代理资产已确认可作为复盘对象。
  - `candidate`：MVP 可用候选，仍需进一步人工确认。
  - `unverified`：逻辑可能相关，但默认不启用。
  - `missing`：缺少可执行映射。
- `validation_status`：provider 实际拉数状态。
  - `live_ok`：真实 provider 已拉到足够价格点。
  - `live_failed`：真实 provider 拉取失败或数据不足。
  - `cache_only`：本地 CSV 或缓存候选。
  - `not_checked`：尚未做 live validation。

## fallback_rank

同一 `asset_name` 可以有多个 proxy candidates。ProviderRouter 排序规则为：

```text
mapping_status: verified > candidate > unverified > missing
validation_status: live_ok > cache_only > not_checked > live_failed
fallback_rank: 越小越优先
confidence: 越高越优先
YAML 顺序最后兜底
```

如果优先 route 的 provider 调用失败，Router 会记录错误并继续尝试下一个可用 candidate。

## validate_provider_routes.py

运行：

```bash
python scripts/validate_provider_routes.py
python scripts/validate_provider_routes.py --event-type ai_export_control
python scripts/validate_provider_routes.py --refresh-cache --write-report
python scripts/validate_provider_routes.py --refresh-cache --write-report --no-proxy
```

默认只验证 `provider=akshare` 的 candidates，不验证 CSV/mock。默认检查最近 60 个自然日，候选的 `min_price_points` 可以覆盖默认阈值。

只有显式传入下面参数才会把 validation metadata 写回 YAML：

```bash
python scripts/validate_provider_routes.py --update-yaml-validation
```

## Report 格式

`--write-report` 会写入：

```text
reports/provider_validation_report.json
reports/provider_validation_report.md
```

每条 route 包含：

```text
event_type
asset_name
proxy_asset_name
provider
provider_type
provider_symbol
mapping_status
validation_status
price_points
error
```

## 测试策略

`pytest` 默认不联网。Provider validation 的默认测试使用 fake provider 返回固定 `PriceSeries`。真实联网测试仅在设置环境变量后运行：

```bash
EVENTALPHA_RUN_LIVE_PROVIDER_VALIDATION=1 pytest tests/integration/test_provider_validation_live.py
```

## 当前限制

AkShare 和 EastMoney 接口可能受网络、代理、字段变化和接口限流影响。`live_ok` 只表示本次验证成功，不表示未来持续可用；`live_failed` 也不必然说明映射逻辑错误。

本内容仅用于事件研究和市场分析，不构成投资建议。市场价格可能已提前反映相关信息，投资决策需结合个人风险承受能力。
