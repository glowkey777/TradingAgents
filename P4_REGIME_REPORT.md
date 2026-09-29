# P4_REGIME_REPORT.md — Regime Engine 报告

## 1. Implementation Summary

多维 Regime Probability：Trend / Volatility / Macro / Event 四维独立，rule-based scoring，PIT-safe，deterministic，versioned。

## 2. Regime 分布（2024-01-01 ~ 2024-06-03，主导状态 argmax）

| 维度 | 分布 |
| --- | --- |
| trend | {'bull_trend': 102, 'bear_trend': 4} |
| volatility | {'low_volatility': 88, 'normal_volatility': 17, 'high_volatility': 1} |
| macro | {'normal_macro': 105, 'macro_shock': 1} |
| event | {'normal_event': 98, 'event_driven': 8} |
| overall_status | {'OK': 106} |

## 3. Probability Semantics

- probability = normalized regime score（规则命中权重归一化），**不是** P(Y|X) 校准概率。
- confidence = data completeness（可用输入比例），**不是** 统计置信度。
- 两者语义严格区分，禁止混淆。

## 4. Missing Data Handling

- 无数据 → status=NOT_AVAILABLE，概率为空 dict（**不填 0/neutral**）。
- 有数据但全 0 → status=INSUFFICIENT_DATA。
- 2013-01-02（数据起点）trend=NOT_AVAILABLE，已验证。

## 5. 验收汇总

| 项 | 结果 |
| --- | --- |
| Regime Models / Registry | ✅ 4 维度 27 规则 |
| Trend / Volatility / Macro / Event | ✅ 各维 sum=1 |
| Multi-dimensional output | ✅ 不压缩成单一字符串 |
| Normalized probabilities | ✅ |
| Rule versioning | ✅ 每规则 version=v1 |
| PIT / Leakage (Test A/B/C/D/E) | ✅ |
| Missing Data (NOT_AVAILABLE) | ✅ |
| INSUFFICIENT_SAMPLE 事件不参与权重 | ✅ |
| Determinism | ✅ |
| Golden Regression | ✅ |
| P1/P2/P3 Immutability | ✅ 只读 |
| Offline pytest | ✅ 108 passed |

## 6. Known Limitations

- probability 是规则得分，未做历史校准（P5 职责）。
- Breadth/Gamma/IV 维度未接入（无合格历史 PIT 数据，故意留空而非伪造）。
- volatility 阈值（VIX<15/<25、rv 0.10/0.20）为 v1 固定值，未做样本外验证。

## 7. P5 Readiness

P4 提供 Market State Layer。P5 可组合 P2 特征 + P3 条件分布 + P4 Regime，计算经过历史验证的 P(T+1 UP/FLAT/DOWN)。P4 不输出 SPY 涨跌概率。
