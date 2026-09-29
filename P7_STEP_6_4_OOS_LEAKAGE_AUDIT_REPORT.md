# P7 STEP 6.4 — OOS Leakage Audit

**STATUS: PARTIAL CLEARANCE（L5 deferred to STEP 6.5）**

---

## 1. 目标

独立、可审计、fail-closed 的 OOS Leakage Audit，验证 STEP 6.3 Prediction Dataset 的每个
prediction record 是否无未来信息/未来修订/未来 outcome/跨样本污染/人为调参泄漏。
本阶段只做 leakage detection，不做 prediction performance / tuning / strategy evaluation。

## 2. Implementation

```
新增 quant_engine/oos/leakage_models.py   OOSLeakageAuditResult / AuditCheck / Violation / CheckStatus
新增 quant_engine/oos/leakage_audit.py    audit_prediction_record / audit_prediction_dataset（L1-L9）
新增 quant_engine/tests/oos/test_leakage_audit.py       17 单元测试
新增 quant_engine/tests/oos/test_leakage_mutation.py    4 mutation 测试
新增 quant_engine/tests/oos/test_leakage_independence.py 5 independence 测试
```

### 关键设计
- **audit 独立于 Builder**：`audit_prediction_record(record, historical_run)` 不信任 `record.pit_status`，
  重新验证 `historical_run.pit_audit` 的 max_available_at/max_revision_time 与 `prediction_as_of`。
- **audit_id deterministic**：sha256(leakage|prediction_id|audit_version)。
- **L3 typed schema**：`FORBIDDEN_OUTCOME_FIELDS` exact field match（非 substring，false-positive 控制）。
- **L4 无跨样本载体**：检查 builder 无 module-level mutable state。
- **L9 config fingerprint**：oos_contract_version/quant_state_version/renderer_version 一致性，检测 CONFIG_DRIFT。
- **NOT_VERIFIED ≠ PASS**：overall = FAIL 优先，其次 NOT_VERIFIED，全 PASS 才 PASS。

## 3. Audit Matrix

| Audit | Status | Evidence |
| --- | --- | --- |
| L1 Temporal | **PASS** | max_available_at <= prediction_as_of |
| L2 Revision | **PASS** | max_revision_time <= prediction_as_of（当前数据源无修订）|
| L3 Label | **PASS** | typed schema + serialized payload 无 outcome 字段 |
| L4 Cross-Sample | **PASS** | builder 无 module-level mutable state |
| L5 Agent Research | **NOT_VERIFIED** | static boundary clean（builder 不依赖 TradingAgents）；interface 需跑 Multi-Agent（DEFERRED_TO_STEP_6_5）|
| L6 QuantState | **PASS** | post-build 无未来行 + source_lineage 完整 |
| L7 QuantContext | **PASS** | renderer_version 绑定 + mutation invariance |
| L8 Thesis | **NOT_APPLICABLE** | PredictionRecord 仅 thesis_id 引用，无 thesis 文本 |
| L9 Tuning | **PASS** | config fingerprint 一致（无 CONFIG_DRIFT）|

## 4. Mutation Tests

```
Future mutation   PASS   T+1/T+2 close → CANARY=999999999，PredictionRecord/QuantState/P5 全部不变
Revision mutation PASS   revision_time > as_of → audit L2 FAIL（fail-closed）
Synthetic canary  PASS   future canary 值绝不得进入 QuantState / PredictionRecord
```

## 5. Audit Independence / Serialization / Hash

```
Audit independence  PASS   BAD_DATASET（篡改 pit_status=PASS 但 source 泄漏）→ audit FAIL
Serialization       PASS   serialize→deserialize 后 system-owned fields 不变
Dataset hash        PASS   same source → same hash；future mutation → hash 不变
False-positive ctrl PASS   typed schema 不 substring（"positive"/"negative" 不误判）
No strategy leakage PASS   audit 源码无 strike/delta/gamma/theta/kelly/position_size/pnl
```

## 6. Tests

```
quant_engine   291 passed / 0 failed   （265 既有 + 26 新增）
TradingAgents  1001 passed + 91 subtests, 5 skipped / 0 failed
```

## 7. Acceptance Gates（A–V）

```
A  Audit independent from Builder   PASS
B  L1 Temporal audit                PASS
C  L2 Revision audit                PASS
D  L3 Label audit                   PASS
E  L4 Cross-Sample                  PASS（builder 无 global state）
F  L5 Agent Research                NOT_VERIFIED（explicit，DEFERRED_TO_STEP_6_5）
G  L6 QuantState                    PASS
H  L7 QuantContext                  PASS
I  L8 Thesis                        NOT_APPLICABLE（schema 无 thesis 文本）
J  L9 Tuning                        PASS（config fingerprint 一致）
K  Future mutation                  PASS
L  Revision mutation                PASS
M  Synthetic canary                 PASS
N  Audit independence test          PASS
O  Serialization audit              PASS
P  Dataset hash audit               PASS
Q  False-positive controls          PASS
R  No strategy leakage              PASS
S  Full regression                  PASS（291 + 1001）
T  No prediction metrics            PASS（NOT RUN）
U  No historical Multi-Agent batch  PASS（NOT RUN）
V  No trading evaluation            PASS（NOT RUN）
```

## 8. 明确说明：L5 未完成 COMPLETE clearance

**L5 Agent Research = NOT_VERIFIED，不是 PASS。**

原因：STEP 6.4 不运行历史 Multi-Agent batch（scope 限制），因此无法证明 agent research 在 T 时刻
不访问 future data / latest web / future news / future outcome。

当前已证明的部分：
- **static boundary**：STEP 6.3 Prediction Dataset 不依赖 TradingAgents research output 构造 P5 概率（P5 概率只来自 QuantState）。
- 待验证的部分：agent research 的 runtime interface 是否允许访问未来数据 → 需 STEP 6.5（Historical Multi-Agent Run）才能审计。

因此：

> **当前 STEP 6.4 不具备 COMPLETE leakage clearance。**
> L5 明确 DEFERRED_TO_STEP_6_5，不伪装 PASS，不用 "PASS with caveat" 掩盖。

## 9. LOCK

```
L1-L4, L6-L9：PASS / LOCK
L5：DEFERRED_TO_STEP_6_5（NOT_VERIFIED）
整体：PARTIAL CLEARANCE，待 STEP 6.5 补 L5 interface audit 后 complete
```

## 10. 明确 NOT RUN

```
Prediction metrics       NOT RUN
Historical Multi-Agent   NOT RUN（L5 interface audit 留待 6.5）
Trading performance      NOT RUN
```

最终原则已遵守：**NO LEAKAGE CLAIM WITHOUT EVIDENCE；NOT_VERIFIED ≠ PASS。**
下一步为 STEP 6.5（Historical Multi-Agent Run），等待指令。
