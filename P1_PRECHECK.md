# P1_PRECHECK.md — P1 开工前检查报告

> 按最终 P1 Prompt 要求，先检查再动代码。本报告 = 汇报 A~I，确认后进入实施。

## A. 当前已有能力

- **TradingAgents v0.5.1**：dataflows/date_window.py（PIT 纪律）、backtest、checkpoint、多 LLM provider。
- **quant_engine/data/**（上一轮已建，验收通过）：`contract.py`（DataPoint 四时间字段）、`pit.py`（raw→PIT 长表）、`adapter.py`（as_of 取数）、`tests/test_pit.py`。
- **OpenD 已接入**：Futu_OpenD PID 47600，端口 11111 LISTENING，SDK 连接成功。
- **yfinance 1.4.1**（hermes venv）：日线/宏观可拉。
- **已有 CSV**：`spy_daily_2013_2026.csv`（OHLCV）、`spy_macro_2013_2026.csv`（6 字段宽表）。

## B. 可复用代码

| 已有 | 复用方式 |
|---|---|
| TradingAgents `dataflows/date_window.py` | PIT 纪律（as_of clamp），不重造 |
| `quant_engine/data/contract.py` | 升级为 `models.py`（MarketDataPoint 加 frequency/timezone/dataset_version） |
| `quant_engine/data/pit.py` | 保留，扩展四时间字段 + frequency |
| `quant_engine/data/adapter.py` | 拆进 `adapters/`（spy/macro/intraday/options） |
| `tests/test_pit.py` | 保留，扩展 negative tests |

## C. 需要新增的代码（按新 Prompt 目录）

```
quant_engine/data/
├── models.py          # MarketDataPoint / OptionDataPoint / DataSourceMetadata（强类型）
├── interfaces.py      # PITDataReader / MarketDataRepository / TradingCalendar Protocol
├── calendar.py        # 交易日历（周末/假期/跨年，禁 timedelta 假交易日）
├── validation.py      # schema/OHLC/重复/缺失/未来数据 校验（flag+report，不无脑删）
├── repository.py      # Parquet canonical storage
├── config.py          # dataset_version、symbol mapping、availability_policy
├── loaders/           # local_csv / yfinance / opend
└── adapters/          # spy / macro / intraday / options
```

## D. OpenD 实际数据能力（已实测）

| 能力 | 结果 | 备注 |
|---|---|---|
| 历史日线 K线 | ✅ | `request_history_kline` 返回**三元组** `(ret, data, page_req_key)` |
| 日内 15m K线 | ✅ 50 行 | 同上三元组 |
| 期权链 | ✅ 350 行/天 | `get_option_chain` 返回**二元组** `(ret, data)`，含 option_type/strike_price/strike_time/expiration_cycle |
| **历史期权链** | ⚠️ 未确认 | get_option_chain 只给当前/近期；能否拉历史期权报价待测 |

**SDK 关键坑**：futu SDK **10.07.6708**，不同 API 返回结构不同（request_history_kline=三元组、get_option_chain=二元组），adapter 必须逐一适配，不能统一假设二元组。

## E. SPY CSV 实际字段与时间范围

- 列：`Date, Open, High, Low, Close, Volume`（**无 Adj Close**）
- 3454 行，2013-01-02 ~ 2026-09-25，无重复、无缺失
- **复权价**（2013-01-02 Close=115.71，真实约 146 → adjusted），metadata 须标 `price_basis=adjusted`
- OHLC 有 **1 处浮点误差**（2018-01-19，High==Close 差 ~1e-9），Validation 需容差

## F. yfinance 数据能力

- `^VIX / ^FVX / ^TNX / DX-Y.NYB / CL=F` 日线均可拉（已拉过，3452 行对齐）
- `^FVX/^TNX` 返回的是**收益率数值**（5.03 即 5.03%），单位需在 mapping 里显式标注，不许凭记忆硬编码

## G. PIT 风险点

1. 复权 vs 未复权：CSV 是复权价，`price_basis` 必须标注，避免与 OpenD（未复权）混用
2. OHLC 浮点误差：Validation 用容差（如 1e-6），不因 1e-9 报错
3. OpenD 时间戳时区：富途返回时区需统一到 UTC/ET
4. 期权历史链不可得：不能拿当前期权链回填历史，标 `unavailable`
5. 2024-06-01 是周六（非交易日）：测试用 2024-05-31 或验证非交易日拒绝

## H. P1 实施计划（11 步）

1. 建 models.py（MarketDataPoint/OptionDataPoint/DataSourceMetadata）
2. 建 interfaces.py（PITDataReader/Repository/Calendar Protocol）
3. 建 calendar.py（交易日历）
4. SPY CSV adapter（读真实结构，含复权标注）
5. yfinance macro adapter（验证 ^FVX/^TNX 单位）
6. OpenD adapter（日线/日内，三元组适配；期权链只测接口记能力，不策略）
7. Normalizer + Validator
8. Parquet Repository
9. PIT Repository
10. 测试（unit/PIT/calendar/validation/repository/OpenD mock）
11. Benchmark + Failure Gate

## I. 发现的阻塞问题

1. **OpenD 历史期权链能力未确认**——需测能否拉历史期权报价/IV/Greeks；不能则 P8 期权回测仍缺数据源（不影响 P1 数据层）。
2. **futu SDK 返回结构不一致**（2/3 元组混用），adapter 需逐一适配。
3. **pytest 未装**（venv 无），需 `pip install pytest` 或继续纯 assert。
4. 复权/未复权双源：SPY CSV（复权）vs OpenD（未复权），Repository 需统一 price_basis，否则同 symbol 两个价。

## 结论

OpenD 接入状态已确认，P1 可按"日线+日内+期权三层 Data Contract"设计。**建议先确认本报告（尤其 I.1 期权历史链、I.4 复权双源），再开始 Step 1 写代码。**
