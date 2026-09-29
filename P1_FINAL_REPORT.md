# P1_FINAL_REPORT.md — P1 数据层最终报告

> 结论：**P1 PASS，可验收，不返工。** 数据层已 LOCK，P2 可直接以只读方式消费。

## 验收矩阵

| 验收项 | 结果 |
|---|---|
| P1 Acceptance（6 基线 + 6 日期回放） | ✅ **22/22** |
| Golden Dataset Regression | ✅ **13/13** |
| P1 Final Audit（三项） | ✅ **3/3** |
| P1.5 全量入库 | ✅ COMPLETE（0 失败） |

## 数据覆盖

| 频率 | 范围 | 交易日 | bars | 缺失 |
|---|---|---|---|---|
| daily | 2013-01-02 → 2026-09-25 | 3454 | 3454 | 0 |
| 15m | 2018-09-21 → 2026-09-25 | 2013 | 52132 | 0 |
| 宏观(VIX/US5Y/US10Y/DXY/WTI) | 2013 → 今 | — | — | — |

## 三项 Final Audit 结论

1. **PIT 覆盖 Daily + 15m** ✅：daily available_at=收盘后 23:59:59；15m available_at=bar 结束时间（09:45=09:30-09:45）；as_of 早于 bar 时间不可见。
2. **session boundary** ✅：15m bar 09:45~16:00，半天交易日 14 bar（感恩节后周五/圣诞前夕/独立日前），timezone=America/New_York，price_basis=unadjusted，adjustment=NONE。
3. **P2 只读接口** ✅：`repository.get/get_history/latest`（只读，带 as_of）+ `write`（P2 禁用，单独隔离）。

## 关键数据边界（探测得出，非假设）

- 15m 历史边界 = **2018-09-21**（2018-09-20 前 = SOURCE_UNAVAILABLE）
- 半天交易日 17 天 + 边界首日 24 bar，全部验证为真实

## 修复的 bug（验收抓出）

1. futu 15m `time_key` 是 bar **结束**时间（非开始），observation_time 多加了 15 分钟 → 已修
2. venv 缺 pyarrow → to_parquet 崩溃 + OpenD 后台线程挂起 420s → 已装 pyarrow

## 交付物清单（`TradingAgents\`）

```
P1_PRECHECK.md          P1_DATA_REPORT.md      P1_ACCEPTANCE.md
P1.5_DATA_INGESTION.md  P1_FINAL_REPORT.md     GOLDEN_DATASET.md
DATA_CONTRACT.md  SPEC.md  ARCHITECTURE.md  ROADMAP.md  OPEN_QUESTIONS.md
quant_engine/data/{models,interfaces,calendar,config,validation,repository,pit,adapter}.py
quant_engine/data/loaders/{opend_loader,yfinance_loader,local_csv}.py
golden_dataset/{manifest.json, raw/, canonical/, validation/, replay/}
data/ingested/{daily,15m}/*.parquet + {ingestion_manifest,data_coverage,partition_manifest}.json
p1_acceptance.py  build_golden_dataset.py  golden_regression.py  ingest_p15.py  finalize_p15.py  p1_final_audit.py
```

## P2 前置状态

- 只读数据接口：`repository.get/get_history/latest(symbol, field, start, end, as_of, dataset_name)`
- 可用数据：SPY 日线(未复权,2013→今) + 15m(未复权,2018→今) + 宏观 5 字段
- Feature 计算必须**继承 P1 PIT**（Raw → P1 PIT → Feature，绝不 Raw → Feature → PIT）
- 每个 Feature 进 **Feature Registry**（name/definition/formula/input_fields/frequency/lookback/availability_rule/PIT_rule/version）
