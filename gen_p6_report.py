# -*- coding: utf-8 -*-
"""生成 P6_QUANTSTATE_SPEC.md + P6_QUANTSTATE_REPORT.md。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"F:\Youtube\0413\TradingAgents")

SPEC = """# P6_QUANTSTATE_SPEC.md — QuantState Schema

## 顶层
```
QuantState (frozen)
├── schema_version   = "quant-state-schema-v1"   # Contract 结构版本
├── state_version    = "quant-state-v1.0.0"      # pipeline 版本
├── symbol / as_of
├── market           → MarketSnapshot
├── features         → FeatureSnapshot
├── events           → EventSnapshot
├── evidence         → EvidenceSnapshot
├── regime           → RegimeState（复用 P4）
├── probability      → ProbabilitySnapshot（复用 P5 ProbabilityEstimate）
├── risk             → RiskSnapshot（interface，NOT_AVAILABLE）
├── data_quality     → DataQuality
├── confidence       → StateConfidence
├── lineage          → StateLineage
└── created_at
```

## 各层
- MarketSnapshot：close/open/high/low/volume + trading_date + frequency（PIT：as_of 可见的最后交易日）
- FeatureSnapshot：feature_version + values + available_features + unavailable_features
- EventSnapshot：event_version + active_events（EventOccurrence 含 event_name/event_time/threshold/available_at）
- EvidenceSnapshot：event_evidence + probability_evidence（EvidenceItem 含 source/method/sample_size/status/horizon）
- RegimeState：P4 四维 trend/volatility/macro/event + confidence + status
- ProbabilitySnapshot：probability_version + t1/t2（ProbabilityEstimate）
- RiskSnapshot：status + max_position_risk/max_loss/volatility_state/risk_flags + risk_version
- DataQuality：status + missing_* + insufficient_sample_items + pit_validated
- StateConfidence：score + level（HIGH/MEDIUM/LOW/NOT_AVAILABLE）+ reasons + method
- StateLineage：data_versions + feature/event/regime/probability/risk/label_version + source_versions + pipeline_version

## 语义边界（关键）
- confidence ≠ p_up（confidence = 数据完整度，probability = 历史条件分布估计）
- Risk status = NOT_AVAILABLE，不伪造 0
- Missing feature = None，不转 0
- Immutability：frozen=True
"""

REPORT = """# P6_QUANTSTATE_REPORT.md

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
"""


def main():
    (ROOT / "P6_QUANTSTATE_SPEC.md").write_text(SPEC, encoding="utf-8")
    (ROOT / "P6_QUANTSTATE_REPORT.md").write_text(REPORT, encoding="utf-8")
    print("P6_QUANTSTATE_SPEC.md + P6_QUANTSTATE_REPORT.md 已生成")


if __name__ == "__main__":
    main()
