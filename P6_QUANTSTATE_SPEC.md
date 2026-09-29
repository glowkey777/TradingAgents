# P6_QUANTSTATE_SPEC.md — QuantState Schema

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
