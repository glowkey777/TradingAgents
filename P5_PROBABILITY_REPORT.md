# P5_PROBABILITY_REPORT.md — Probability Engine 报告

## 1. Architecture

Baseline 先行（非 ML）：P2 Features + P3 Events + P4 Regime → 历史相似状态 → 条件 label 分布 → Laplace 平滑 → P(UP/FLAT/DOWN)。walk-forward PIT，temporal split 评价。

## 2. Probability Semantics

- 概率 = 历史相似样本的 label 条件分布（Laplace 平滑），非 ML 校准概率。
- UP + FLAT + DOWN = 1（tolerance 1e-6）。
- 每个估计记录 evidence_level（实际使用的证据层级）+ sample_size。

## 3. Baseline Comparison（test 期 2024-01-01 ~ 2026-09-25）

| Model | Horizon | N | Log Loss | Brier | 备注 |
| --- | --- | ---: | ---: | ---: | --- |
| baseline_unconditional | T+1 | 686 | 1.0745 | 0.6509 | |
| baseline_unconditional | T+2 | 686 | 1.0723 | 0.6483 | |
| baseline_regime_conditional | T+1 | 686 | 1.0877 | 0.6579 | |
| baseline_regime_conditional | T+2 | 686 | 1.0916 | 0.6613 | |
| baseline_event_conditional | T+1 | 686 | 1.0724 | 0.6494 | |
| baseline_event_conditional | T+2 | 686 | 1.0713 | 0.6478 | |
| baseline_hierarchical | T+1 | 686 | 1.0750 | 0.6500 | |
| baseline_hierarchical | T+2 | 686 | 1.0808 | 0.6531 | |

随机均匀基线（log(3)）= 1.0986 Log Loss / 0.6667 Brier。

## 4. 关键发现

- Event Conditional 相比 Unconditional 仅**微弱改善**（Log Loss 1.0745→1.0724），不足以宣称可靠预测优势。
- Regime Conditional（trend+vol+macro+events 精确匹配）反而更差——条件越精确 → 状态空间稀疏化 → 样本稀少 → Laplace 平滑占比变大 → 概率向 1/3 收缩 → 预测能力下降。
- 严格结论：**Baseline 未发现具有经济意义或统计上充分证据的信息增益**；Event Conditional 仅微弱改善，Regime Conditional 因条件样本稀疏反而恶化。不做参数调优粉饰。

## 5. 验收汇总

| 项 | 结果 |
| --- | --- |
| Probability Model / Registry | ✅ 4 baseline |
| T+1 / T+2 Probability | ✅ |
| P3 Evidence / P4 Regime | ✅ |
| Similarity | ✅ z-score 接口 |
| Hierarchical fallback | ✅ 5 层记录层级 |
| Sample-size gate | ✅ 3 级 |
| Smoothing (Laplace alpha=1.0) | ✅ |
| Temporal Split（非 random） | ✅ |
| Log Loss / Brier | ✅ |
| Calibration interface | ✅（status: NOT_CALIBRATED） |
| PIT / Leakage / Determinism | ✅ |
| Golden | ✅ |
| Lineage | ✅ version 全链路 |
| P1-P4 Immutability | ✅ |
| Offline pytest | ✅ 132 passed |

## 6. Known Limitations

- Baseline 未发现经济意义或统计上充分的 edge（Event Conditional 仅微弱改善），未来需 similarity/连续特征增强。
- Calibration 仅实现 interface，status=NOT_CALIBRATED；真正的 calibration curve/ECE 需后续模型 + 独立 OOS 预测再评估。
- 未实现 Model D（regime+event+feature similarity）。

## 7. P6 Readiness

P5 提供 PIT-safe 的概率估计基线 + 评价框架（Log Loss/Brier/Calibration）。P6 可将结构化 ProbabilityEstimate 注入 TradingAgents 做解释/反证。
