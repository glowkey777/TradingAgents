# P7 STEP 6.1 — OOS Evaluation Contract v1.0.0

**STATUS: PASS / LOCK**

---

## 1. 目标

冻结一个可执行、可审计、PIT-safe、不可歧义的「OOS Evaluation Contract v1.0.0」，
用于后续 STEP 6.2+ 的历史样本外预测质量评估。本阶段只定义 + 冻结，不运行历史批量、
不生成预测数据集、不跑 Multi-Agent 历史回测、不做任何策略/期权/仓位/收益率评估。

## 2. 从现有实现确认的语义（先取证，不自行假定）

| 语义 | 来源 | 确认值 |
|---|---|---|
| prediction cutoff | `data/pit.py` | `available_at = T 日 23:59:59 UTC`（收盘后可用）→ **正式 as_of = T 日收盘后** |
| PIT 边界 | `data/adapter.py` | `available_at <= as_of` 才可见 |
| 四时间字段 | `data/pit.py` | observation_time / published_at / available_at / revision_time |
| 交易日历 | `data/calendar.py` | 真实交易日集合（next_session/previous_session，非 calendar day +1） |
| Label | `labels/definitions.py` | T+1/T+2 三分类，threshold = 0.5 × realized_vol_20(T)/√252 |
| Label 计算 | `labels/generator.py` | fwd = close[T+n]/close[T]−1；UP/FLAT/DOWN；endpoint 缺失→不生成（非 FLAT） |
| 概率来源 | `probability/estimator.py` | P5 hierarchical，Laplace α=1.0，min sample 30 / low 100 |
| Temporal split | `probability/pipeline.py` | train 2013-2020 / validation 2021-2023 / test 2024-2026-09-25 |
| 指标 | `probability/pipeline.py` | Log Loss / Brier（三分类），N=686（test 期） |

**关键结论**：smoke-test 的 `2024-06-03T23:59:59` 与正式 OOS cutoff 一致（都是 T 日收盘后），
但 STEP 6.1 把正式 cutoff 冻结为 `POST_CLOSE`（选项 C），不依赖 smoke-test 的 as_of 作为默认假设。

## 3. Contract 内容（contract.py + models.py + validation.py）

### 3.1 Evaluation Unit（唯一身份，deterministic）
`evaluation_id = symbol + prediction_date + horizon + contract_version`
→ 相同 symbol+T+horizon+version 重复运行必得相同 identity。

### 3.2 Prediction Object
prediction_date / symbol / horizon / p_up / p_flat / p_down / directional_bias /
confidence / thesis_id / run_id / quant_state_version / renderer_version / model_provenance。
约束：p_up+p_flat+p_down=1（tolerance 1e-6），概率必须来自 P5（拒绝 LLM/manual/second engine）。

### 3.3 Label Contract
直接引用 P3 frozen（t1_up_flat_down / t2_up_flat_down），不重新发明。
label 使用 T+1/T+2 未来数据合法，但**只能进入 evaluation label，绝不进入 prediction-time state/context/research/thesis**。

### 3.4 Leakage Taxonomy（L1-L9）
L1 temporal / L2 revision / L3 label / L4 cross-sample / L5 agent-research /
L6 quantstate / L7 context / L8 thesis / L9 tuning。

### 3.5 Missing-data semantics（禁止 None→0/neutral/average）
VALID / INSUFFICIENT_SAMPLE / NOT_AVAILABLE / NOT_EVALUABLE / PIT_VIOLATION / INVALID。
PIT_VIOLATION = 预测侧发现未来信息进入 T pipeline，不得简单 skip，记严重 audit failure。

### 3.6 Metrics（沿用 P5）
主指标：Log Loss / Brier（三分类 UP/FLAT/DOWN）。
次指标：Accuracy / Directional Accuracy（secondary / descriptive，非核心）。

### 3.7 Baselines（沿用 P5，不新增）
baseline_unconditional（无条件历史分布）+ uniform reference（log(3)=1.0986 / Brier=0.6667）。

### 3.8 明确排除
Prediction Quality ≠ strategy profitability；禁止把 prediction accuracy 解释为 SPY 价差盈利；
禁止 p_up → option trade → PnL。STEP 6 只回答预测概率是否具信息价值。

## 4. Acceptance Gates（A–Q）

```
A  prediction time 明确定义          PASS  (POST_CLOSE，T 日收盘后 23:59:59 UTC)
B  PIT boundary 明确定义             PASS  (available_at <= as_of)
C  available_at/revision 语义明确     PASS  (四时间字段 + revision_time > as_of 禁止)
D  T+1/T+2 trading-day 语义明确       PASS  (真实交易日，非 calendar day +1)
E  P3 label 完整复用                 PASS  (直接引用 frozen，未重发明)
F  P5 probability 完整复用           PASS  (概率唯一来源 P5)
G  prediction/outcome 完全隔离       PASS  (PredictionRecord 无 outcome 字段)
H  OOS temporal split 冻结           PASS  (train/validation/test，与 P5 一致)
I  leakage taxonomy 完整             PASS  (L1-L9)
J  missing-data semantics 完整       PASS  (6 状态)
K  reproducibility contract 完整      PASS  (evaluation_id deterministic + provenance 必录)
L  metrics contract 完整             PASS  (Log Loss/Brier 主 + Accuracy 次)
M  baseline contract 完整            PASS  (unconditional + uniform reference)
N  trading-performance 明确排除      PASS  (NON_SCOPE_NOTE)
O  contract versioned               PASS  (v1.0.0，immutable after lock)
P  tests 全绿                        PASS  (20/20)
Q  P1-P7 regression 全绿             PASS  (221 + 1001)
```

## 5. Files

```
新增 quant_engine/oos/__init__.py
新增 quant_engine/oos/contract.py        contract 常量 + 冻结语义
新增 quant_engine/oos/models.py          EvaluationUnit/PredictionRecord/OutcomeRecord/OOSContract + 枚举
新增 quant_engine/oos/validation.py      PIT boundary / trading-day / revision / determinism 验证
新增 quant_engine/tests/oos/__init__.py
新增 quant_engine/tests/oos/test_contract.py   20 contract tests
本报告 P7_STEP_6_1_OOS_EVALUATION_CONTRACT.md
（P1-P7 frozen contract / graph topology / probability / regime / QuantState 零改动）
```

## 6. Tests

```
quant_engine  221 passed / 0 failed   （201 既有 + 20 新增 OOS contract）
TradingAgents 1001 passed + 91 subtests, 5 skipped / 0 failed
```

## 7. Regression

```
P1-P7 REGRESSION: PASS
```

## 8. 已知差异 / 记录

- P5 的 TEMPORAL_SPLIT（probability baseline evaluation split）与 OOS Multi-Agent split 无定义差异，
  直接沿用并冻结为 OOS_TEMPORAL_SPLIT；未修改 P5。
- 当前数据源 revision_time 全为 NaT（无修订），revision leakage 规则已定义但当前数据不会触发；
  保留规则以防未来数据源引入修订。

## 9. LOCK

```
STEP 6.1 = PASS / LOCK
OOS Evaluation Contract v1.0.0（immutable after lock；修改需新版本）
```

严格停止：不运行历史 Multi-Agent、不生成 OOS prediction dataset、不计算历史预测表现。
下一步为 STEP 6.2（Historical Point-in-Time Runner），等待指令。
