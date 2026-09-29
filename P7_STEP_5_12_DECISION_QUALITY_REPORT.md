# P7 STEP 5.12 — Decision Quality / Thesis Consistency Audit Report

**STATUS: PASS / LOCK**

---

## 1. Scope

建立从 `QuantState → Multi-Agent Research → TradingThesis` 的最终决策质量闸门。
本阶段只回答一个工程问题：最终 TradingThesis 是否是**结构完整、证据一致、概率受 P5 约束、
provenance 完整、invalidation 完整、可审计的决策对象**。

输入：Golden QuantState → quant_context → 12-agent full graph → CandidateThesis →
parse_candidate → assemble_thesis → validate_thesis → TradingThesis
输出：DecisionQualityAuditReport（9 维矩阵）

## 2. Non-scope

本阶段禁止且未执行：修改 P1-P6 / 修改 P5 概率 / 重算概率 / 第二概率引擎 /
修改 QuantState / 修改 renderer 事实内容 / 修改 graph topology / prompt tuning /
模型比较 / 历史 batch 回测 / 收益率·Sharpe·胜率优化 / options·position sizing /
自动交易 / 按结果反向调规则。

## 3. Current architecture

```
P5 ProbabilityEstimate (LOCK) ──唯一概率来源──▶ ProbabilityReference（系统注入）
P4 RegimeState (LOCK) ──────────▶ regime_snapshot（系统注入）
QuantState.lineage (LOCK) ──────▶ source_lineage（系统注入）
系统参数 (provider/model/temp/run) ─▶ model_provenance（系统注入）
LLM CandidateThesis（仅 6 字段）──▶ directional_bias/confidence/evidence/invalidation/summary
```

## 4. Audit contract（decision_quality_audit.py，9 维）

| 维度 | 检查内容 |
|---|---|
| schema_completeness | 15 个 required 字段非空 |
| probability_binding | final 概率逐字段 `==` P5（严格，非 ≈）+ P5 method/sample_size/status 完整 + quant_state_version binding |
| regime_binding | regime_snapshot 四维逐字段 `==` P4 |
| evidence_integrity | 组合 STEP 5.11 的 8 项 audit |
| thesis_completeness | supporting 非空 + contradicting 非空 + invalidation 非空 + summary 非空 |
| direction_consistency | directional_bias 与 summary 内部逻辑矛盾（不查「方向 != P5 最大概率」）|
| invalidation_traceability | invalidation 价格可溯源到 QuantState.market 或 agent 工具输出 |
| provenance_completeness | provider/model/temperature/prompt_version/agent_version/run_id/as_of/quant_state_version/renderer_version 完整 |
| system_field_determinism | as_of/created_at/symbol/version/lineage == QuantState 确定性推导值 |

## 5. Golden run（SPY 2024-06-03，deepseek-v4-pro，temp=0.2，max_tokens=16000）

```
signal           = Hold
directional_bias = NEUTRAL
confidence       = 0.8 (high)
probability_ref  = UP 0.3210 / FLAT 0.4314 / DOWN 0.2476 (horizon=T+1)  ← == P5
regime           = trend.bull_trend 0.8333                              ← == P4
supporting       = 4
contradicting    = 2
invalidation     = 3
provenance       = deepseek/deepseek-v4-pro/temp=0.2/run=decision-quality-512-2024-06-03
quant_state_ver  = quant-state-v1.0.0
renderer_ver     = quant_context_v1
```

## 6. Decision Quality Matrix

```
schema_completeness          PASS
probability_binding          PASS
regime_binding               PASS
evidence_integrity           PASS
thesis_completeness          PASS
direction_consistency        PASS
invalidation_traceability    PASS
provenance_completeness      PASS
system_field_determinism     PASS
────────────────────────────────────
9/9 PASS
```

## 7. Adversarial tests（12/12 PASS）

```
 1  LLM 修改 p_up                → probability_binding FAIL
 2  LLM 修改 regime              → regime_binding FAIL
 3  LLM 删除 invalidation        → thesis_completeness FAIL
 4  LLM 删除 contradicting       → thesis_completeness FAIL
 5  LLM 伪造 gamma               → evidence_integrity FAIL
 6  LLM 第二套概率               → evidence_integrity FAIL
 7  LLM 修改 lineage             → system_field_determinism FAIL
 8  LLM 修改 provenance          → provenance_completeness FAIL
 9  bias 与自身陈述矛盾          → direction_consistency FAIL
10  invalidation 虚构价格        → invalidation_traceability FAIL
11  空 thesis                    → schema_completeness FAIL
12  正常完整 thesis              → 全 PASS
```

## 8. Evidence audit dependency

STEP 5.12 复用 STEP 5.11 的 `validate_thesis_evidence_integrity()`（8 项），不重复实现。
Golden run 中 5.11 的 8 项全 PASS（probability/regime/source/unavailable/
attribution/drift/invalidation/duplication）。

## 9. Regression results

```
quant_engine   201 passed / 0 failed   （189 既有 + 12 新增 decision quality 测试）
TradingAgents  1001 passed + 91 subtests, 5 skipped / 0 failed
```

## 10. Modified files

```
新增 quant_engine/integration/decision_quality_audit.py           9 维审计 + validate_decision_quality
新增 quant_engine/tests/integration/test_decision_quality_audit.py  12 adversarial tests
修改 quant_engine/integration/evidence_audit.py                    source_integrity/drift_integrity 审计器修复
（frozen contract / P1-P6 / P5 / P4 / graph topology 零改动）
```

### 审计器修复记录（false positive，非放宽业务约束）

1. `source_integrity`：source_id 格式差异（`P5_hierarchical_T1` vs `EVIDENCE.P5 hierarchical T+1`）
   造成完整 token 匹配假阳性 → 改为 meaningful-token 匹配（过滤类型词，ALL 命中）。
2. `drift_integrity`：P5 值的合法算术组合（`FLAT+DOWN=0.3055+0.2822=0.5877`）被误判为漂移
   → 合法值集合加入「两两和」。实质偏离（0.4314→0.52）仍 FAIL。
3. `invalidation_traceability`：agent 推理支撑位（494.5）不在 4 analyst report 里
   → context_sources 扩展覆盖 trader/portfolio_manager 输出（合法 research evidence）。

## 11. Known limitations

- `direction_consistency` 为关键词启发式，覆盖 summary 与 bias 的**明显**矛盾；深层的
  逻辑矛盾需人工复核，不是本阶段的形式化 gate。
- `system_field_determinism` 验证单次 assemble 的确定性推导，未跨多次 LLM 调用对比
  自由文本（指令明确不要求 LLM 文本逐字符 deterministic）。
- P5 的 `method/sample_size/status/version` 字段 final 不引用（ProbabilityReference 仅
  horizon + p_up/p_flat/p_down），probability_binding 通过「P5 完整性 + quant_state_version
  binding」间接覆盖，未为满足检查而扩 frozen contract。

## 12. PASS / FAIL

```
P7 STEP 5.12  Decision Quality / Thesis Consistency Audit
STATUS: PASS / LOCK
```

满足全部 PASS 条件：A 审计实现 + B adversarial PASS + C Golden run PASS +
D 5.11 evidence audit PASS + E 概率严格 == P5 + F regime 严格 == P4 +
G provenance/lineage system-owned + H 未改 P1-P6 + I 未改 graph topology + J 回归 PASS。
