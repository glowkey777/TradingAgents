# P6_QUANTSTATE_REPORT.md

## 1. Objective
将 P1→P5 的研究结果封装成强类型、immutable、PIT-safe、可序列化、可追溯的 QuantState Contract，供 TradingAgents 稳定消费。P6 不提升预测能力。

## 2. Architecture
```
P1 Data → P2 Features → P3 Event+Label → P4 Regime → P5 Probability
                              ↓
                      P6 QuantState (Contract)
                              ↓
                       TradingAgents / LLM
```

## 3. Schema
见 P6_QUANTSTATE_SPEC.md（13 个强类型层，frozen，schema_version + state_version 分离）。

## 4. PIT
- observation_time = as_of 可见的最后交易日（load_wide 按 available_at <= as_of 过滤）。
- 盘中 as_of=10:00 看不到当天 23:59:59 才可用的收盘（Test A 验证）。
- 所有 event available_at <= as_of（validation 检查）。

## 5. Lineage
data(p1_canonical_v1) → feature(v1) → event(v1) → regime(v1) → probability(v1) → state(p6_v1)；
source_versions 区分层（p2/p3/p4/p5）。

## 6. Missing Data
NOT_AVAILABLE（Risk 未实现）/ INSUFFICIENT_SAMPLE（概率样本不足）/ INSUFFICIENT_DATA（regime 维度）；
均不转 0/neutral，保留语义。

## 7. Serialization
model_dump_json() 确定性（字段顺序 + ISO-8601 datetime）；round_trip 通过。

## 8. Tests
existing（P1-P5）132 passed + new（P6 state）24 = 156 passed / 0 failed，全离线 deterministic。

## 9. Acceptance Matrix
| 项 | 结果 | | 项 | 结果 |
| --- | --- | --- | --- | --- |
| Strong Type | ✅ | | PIT | ✅ |
| QuantState Schema | ✅ | | Leakage A-E | ✅ |
| Market/Feature/Event/Evidence Snapshot | ✅ | | Immutability | ✅ |
| Regime/Probability Integration | ✅ | | Serialization/Round Trip | ✅ |
| Risk Interface | ✅ | | Determinism | ✅ |
| Data Quality | ✅ | | Golden Regression | ✅ |
| Confidence Semantics | ✅ | | Missing Data Semantics | ✅ |
| Lineage | ✅ | | Versioning | ✅ |
| TradingAgents Adapter | ✅ | | P1-P5 Immutability | ✅ |

## 10. Known Limitations
- Risk Engine 未实现（interface 就绪，status=NOT_AVAILABLE）
- Calibration 未实现（P5 遗留）
- LLM reasoning 未接入（P6 只定义消费边界）
- 概率无稳定 edge（P5 baseline 结论）
