# P1_DATA_REPORT.md — P1 数据层完成报告

## 1. Modified files
- `quant_engine/data/contract.py`：保留（DataPoint 四时间字段，向后兼容）
- `quant_engine/data/pit.py` / `adapter.py`：保留（日线 PIT 长表 + as_of 取数）
- `DATA_CONTRACT.md`：加 §0 Canonical Price 决策（未复权）

## 2. New files
```
quant_engine/data/
├── models.py          # MarketDataPoint / OptionDataPoint / DataSourceMetadata（强类型）
├── interfaces.py      # TradingCalendar / PITDataReader / MarketDataRepository (Protocol)
├── calendar.py        # 交易日历（真实交易日集合，非 timedelta）
├── config.py          # dataset_version / symbol mapping / canonical 决策
├── validation.py      # OHLC/重复/未来数据/缺失 校验 + Failure Gate
├── repository.py      # Parquet canonical + PIT 读取
└── loaders/
    ├── opend_loader.py      # OpenD canonical（日线+15m+期权探测）
    ├── yfinance_loader.py   # 宏观
    └── local_csv.py         # CSV 交叉验证（复权价隔离）
```

## 3. Architecture
```
OpenD(未复权 canonical) / yfinance(宏观) / CSV(交叉验证)
        ↓ loader → MarketDataPoint(强类型, 四时间字段)
        ↓ validation → Failure Gate
        ↓ ParquetRepository → PIT 读取(available_at <= as_of)
```

## 4. Data sources
| 源 | 角色 | price_basis |
|---|---|---|
| OpenD | **canonical**（SPY 日线+15m+期权） | unadjusted |
| yfinance | 宏观（VIX/US5Y/US10Y/DXY/WTI） | unadjusted |
| CSV | 历史交叉验证 | adjusted（隔离，不混用） |

## 5. Symbol mappings（yfinance）
`^VIX`(index) `^FVX`(percent) `^TNX`(percent) `DX-Y.NYB`(index) `CL=F`(usd)

## 6-8. Data ranges / rows / missing
- OpenD SPY 日线：**2013-01 至今可拉**（能力已测）；本次集成窗口 2026-08-03 ~ 09-25 = 195 条（33 交易日 × 6 字段）
- CSV：spy_daily 3454 行、spy_macro 3452 行，0 缺失
- missing sessions：未做全量扫描（分页限制，见 §18）

## 9. Anomalies
- CSV 复权价 2018-01-19 有 1 处浮点误差（High==Close 差 ~1e-9），validation 容差 1e-6 已吸收
- WTI 负值（2020-04）在宏观数据里，Feature 阶段处理

## 10. PIT implementation
`MarketDataPoint.visible_at(as_of)`：`available_at > as_of` 或 `revision_time <= as_of` → 不可见。
实测：as_of=2026-09-23 时，09-24/25 收盘不可见 ✅

## 11. Calendar implementation
`TradingCalendar` 从真实交易日集合构建，正确识别 2024-06-01（周六）非交易日、previous_session 正确。

## 12. OpenD capabilities（实测）
- 日线 K线 ✅（2013 至今可拉）、15m K线 ✅、期权链 ✅（350 行/天）
- futu SDK 10.07：request_history_kline=三元组、get_option_chain=二元组

## 13. Options capabilities
- realtime/recent 期权链 ✅（含 option_type/strike_price/strike_time/expiration_cycle）
- **历史期权链 ❓未确认**（get_option_chain 只给当前；P8 再定数据源，P1 不阻塞）

## 14. Dataset versions
`spy_daily_v1` / `opend_intraday_v1` / `macro_daily_yf_v1` / `opend_options_v1`

## 15. Tests
`test_pit.py`（日线 PIT 4 项）✅ + `test_p1_integration.py`（全链路 6 步）✅

## 16. Benchmark
OpenD SPY 日线(2026-08~09)：195 条，字段 close/high/low/open/volume，0 重复/0 缺失/0 未来/0 OHLC 违例

## 17. Failure Gate
**PASS ✅**（duplicates=0, future_data=0, null=0）

## 18. Known limitations
1. OpenD 全量 2013-2026 日线需**分页**（max_count=1000），本次只验证机制 + 近期窗口
2. 历史期权链能力未确认（P8 接专门源或探测 OpenD）
3. pytest 未装（测试用纯 assert + 集成脚本）
4. CSV 复权价与 OpenD 未复权价已隔离，但全量 canonical 历史库待全量拉取后建立

## 19. P2 prerequisites
- 需要：全量 OpenD 日线（分页拉取 2013-2026）+ 宏观数据入库
- Feature Engine 输入就绪：SPY 日线 OHLCV（canonical 未复权）+ 宏观 5 字段
