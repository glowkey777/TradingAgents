# P1_ACCEPTANCE.md — P1 验收基线（锁定）

> 验收结果：**22/22 PASS**（`p1_acceptance.py`，2026-09-27 实测）。不全量入库，P1 核心契约在此锁定。

## ① 六项基线

| # | 项 | 结果 |
|---|---|---|
| 1 | PIT 四时间字段（timestamp/observation_time/available_at/ingested_at/revision_time + as_of 查询参数） | ✅ |
| 2 | visible_at(as_of) 严格禁止未来数据（收盘前不可见/available_at 可见/前一日不可见） | ✅ |
| 3 | OpenD 日线 vs 15m 时间戳/session 一致（15m 首根 09:45 末根 16:00，日线 close==15m 末根 close，session 16:00 一致） | ✅ |
| 4 | 2013→今天日期断层（CSV 3454 交易日，0 处间隔>4天） | ✅ |
| 5 | 15m 异常/重复/跨 session（390 条 3 天，0 重复 0 跨session 0 OHLC违例） | ✅ |
| 6 | 期权链 as_of PIT（OptionDataPoint.visible_at） | ✅ |

## ② 小规模回放（6 日期）

2013-01-02 / 2020-03-16 / 2024-01-02 / 2026-09-23 / 09-24 / 09-25

每个日期：OpenD → loader → canonical → PIT → validation → DB → read-back
**写=读=as_of 可见** 全部通过（写5=读5，gate=PASS，收盘后可见5/盘中可见0）。

## 验收抓出的 bug（已修）

- futu 15m `time_key` 是 **bar 结束时间**（首根 09:45=09:30-09:45，末根 16:00=15:45-16:00），非开始时间。已修正 observation_time：日内用 time_key 本身，不再 +interval。

## OPTION_CHAIN 状态（区分两层）

| 层 | 状态 |
|---|---|
| realtime_recent | VERIFIED（能拉当前链，350 行/天，含 strike/expiration/type） |
| historical_pit_reconstruct | UNVERIFIED（能否重建"历史时点当时的链"，P8 验证，非"现在查历史"） |

## 下一步（不混入 P1 核心验收）

```
P1 FINAL ACCEPT ✅
     ↓
Golden Dataset（锁 6 个回放日的规范样本 + checksum）
     ↓
P1.5_DATA_INGESTION（独立任务：全量 2013→今天分页/分批/幂等/可断点续传/partition 元数据）
     ↓
P1 LOCK
     ↓
P2（Feature Engine）
```

P1.5 全量入库按年份/月 partition，每个 partition 记录 source/request/start/end/rows/duplicates/missing/future_rows/checksum/status/timestamp，支持 OpenD 数据修正时只重跑受影响 partition。
