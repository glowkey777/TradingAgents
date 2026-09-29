# DATA_CONTRACT.md — 数据契约（P1 核心）

> 定义字段、时间语义、频率、时区、缺失值、修订规则。回测只能读决策时点真正可用的版本。

## 0. Canonical Price 决策（用户拍板，最高优先级）

| 项 | 决策 |
|---|---|
| SPY OHLCV canonical | **OpenD 未复权价**，frequency = `1D` + `15m`，`adjustment = NONE` |
| Options | realtime/recent = OpenD；historical = 能力探测（OPTION_CHAIN_SOURCE=OpenD，不支持则 P8 接专门历史源） |
| CSV（spy_daily/spy_macro） | **历史补充/交叉验证**，不作为 canonical price |
| 复权规则 | **禁止数据层偷偷做复权转换**；所有 adjustment 显式记录在 DataContract + metadata（`price_basis` / `adjustment` 字段） |
| 混用禁止 | 复权价不得直接与 OpenD 未复权价混合计算 |

**原则**：一个 canonical price，日线、15m、期权全部围绕同一未复权价格体系。

## 1. PIT 四时间字段（替代单一 available_at）

```python
class DataPoint(BaseModel):
    symbol: str            # "SPY" / "CPI" / "VIX"
    field: str             # "close" / "core_cpi_yoy"
    value: float
    observation_time: datetime   # 数据反映的时点（CPI 反映的月份、K线所在的交易日）
    published_at: datetime       # 官方发布时间（CPI 08:30；市场数据=收盘时刻）
    available_at: datetime       # 真正可用 = max(published_at, 采集延迟)
    revision_time: datetime | None  # 被修正的时间（GDP 二次修正）；None=未修正
```

**回测取数规则**：`as_of = D` 时，只有 `available_at <= D` 且 `revision_time is None or revision_time > D` 的记录可见。

**语义对照**（本系统内统一）：
- 日线 OHLCV：`observation_time = published_at = available_at = 该交易日收盘 16:00 ET`，`revision_time = None`（不复权修订；复权因子单独存）。
- CPI/NFP 等宏观：`observation_time`=反映月份、`published_at`=官方发布时间、`available_at`=发布时间（采集延迟≈0）、`revision_time`=后续修正。
- 没有历史版本记录的数据（如部分 vendor 快照）**不得假设它满足 PIT**，必须标 `pit_quality: unknown`，回测里降级为"仅实盘可用"。

## 2. 频率与时区

- **时区**：统一存储 UTC；展示层转 ET（`America/New_York`）。
- **交易日历**：美股 NYSE 日历（yfinance 自带交易日，缺日用前值补齐并标记 `backfilled`）。
- **频率**（决策后：日线优先 MVP）：
  - P1~P4 用**日线**：预测次日、未来 2 交易日。
  - 30m / 1h / 收盘 日内预测**延后**到日内数据就绪（OpenD 连上后），不做"用日线模拟日内"的假象。

## 3. 三层数据架构

| 层 | 目录 | 内容 | 谁维护 |
|---|---|---|---|
| Raw | `data/raw/` | vendor 原始数据，不加工 | fetch_data.py |
| PIT | `data/pit/` | 四时间字段标准化 | pit 模块 |
| Adapter | `data/adapter.py` | 按 as_of 返回可见数据视图 | Quant Engine 调用 |

**关键**：Quant Engine 复用 TradingAgents `dataflows/date_window.py` 的 PIT 纪律，**不重造第二套 PIT**。同一 SPY 只有一个价格源头。

## 4. 缺失值与修订规则

- 缺失：标注 `missing_reason`（未开盘/数据源断/尚未发布），回测里缺失≠0，也不前值硬填，单独标记。
- 修订：`revision_time` 存在时，回测用修订前的旧值（快照），不静默用新值。
- 对齐：多源合并按 `available_at` 对齐，不按 `observation_time` 硬对齐（避免"用未来才发布的数据对齐过去"）。

## 5. Feature/Data Dependency Matrix（P4 输入依赖核对）

| 数据/特征 | 是否存在 | 有历史吗 | 有 PIT 版本吗 | 频率 | 缺失处理 | 需额外源/Key |
|---|---|---|---|---|---|---|
| SPY 日线 OHLCV | ✅ | ✅ 2013+ | ✅（收盘可用） | 1d | 前值+标记 | 无（yfinance） |
| VIX | ✅ | ✅ | ✅ | 1d | 前值 | 无 |
| US5Y/US10Y | ✅ | ✅ | ✅ | 1d | 前值 | 无 |
| DXY | ✅ | ✅ | ✅ | 1d | 前值 | 无 |
| WTI | ✅ | ✅ | ✅（注意 2020-04 负值） | 1d | 前值 | 无 |
| **Breadth（涨跌家数）** | ❌ | ❌ | ❌ | 1d | — | **需新源**（OpenD/付费） |
| **Gamma / GEX** | ⚠️ 部分（当日） | ❌ 10年 | ❌ | 实时 | — | **不能回填10年**，只做近期 |
| **期权链（IV/报价）** | ⚠️ 当日 | ❌ 10年 | ❌ | 实时 | — | **需 OpenD**，只做近期 |

**结论**：P4 的 Breadth/Gamma 输入在 P1~P3 阶段**不可得**，Regime 引擎第一版只用 Trend/VIX/Yield/Volatility（有历史数据的），Breadth/Gamma 留接口，数据就绪后再接入。
