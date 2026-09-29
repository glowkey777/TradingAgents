# P7 STEP 6.3 — Prediction Dataset

**STATUS: PASS / LOCK**

---

## 1. 目标

建立严格由 STEP 6.2 PIT Runner 产生的 OOS Prediction Dataset Contract + Builder。
核心问题：能否把每个历史预测时点 T，以统一、可审计、不可污染未来数据的结构记录。
本阶段不计算任何预测指标（Log Loss/Brier/Accuracy 全部留后续 evaluation stage）。

## 2. Implementation

```
新增 quant_engine/oos/dataset_models.py   PredictionRecord / PredictionDataset / DatasetManifest
                                          + RecordStatus + FORBIDDEN_OUTCOME_FIELDS + hash 函数
新增 quant_engine/oos/dataset_builder.py  build_prediction_record / build_prediction_dataset / serialize_dataset
新增 quant_engine/tests/oos/test_prediction_dataset.py   25 adversarial tests
```

### 关键设计
- **prediction_id deterministic**：`sha256(symbol|date|as_of|horizon|contract_version)`，无 random UUID/datetime.now。
- **概率 exact-source**：`build_prediction_record` 只从 `HistoricalRunResult.p5_probability` 读 P5 值（copy exactly），
  不 normalize、不重算；invalid sum → `ValidationError`（fail closed，不在 builder 内修正）。
- **prediction-side only**：`FORBIDDEN_OUTCOME_FIELDS` schema-level guard（future_close/future_return/label/...），
  且 `build_prediction_record` 签名只收 `HistoricalRunResult`，不收 raw future market data。
- **PIT_VIOLATION fail-closed**：非 VALID 状态保留 `prediction_id` + `failure_reason`，不 drop（不虚抬 coverage）。
- **duplicate fail-closed**：`prediction_id` 重复 → `DuplicatePredictionIdError`（不 keep first/overwrite）。
- **deterministic ordering**：date ASC → symbol ASC → horizon ASC → id ASC。
- **canonical serialization**：Parquet（schema/column/null/sort/version 明确），CSV 仅兼容导出。
- **hash**：schema_hash / dataset_hash / manifest_hash 均不含 created_at / random / machine path。

## 3. Golden

```
2024-06-03  PASS   T+1 UP=0.3210/FLAT=0.4314/DOWN=0.2476（frozen P5 完整保留，未重算）
2020-03-16  PASS   概率完整（和为 1），directional_bias 从 P5 概率 argmax 推导（非 regime 硬编码）
```

## 4. Integrity

```
Probability source  PASS   （P5 exact-source；篡改 P5 p_up → dataset 反映新值 + hash 变化）
Outcome exclusion   PASS   （schema-level FORBIDDEN_OUTCOME_FIELDS guard + round-trip 无 outcome 列）
PIT guard           PASS   （PIT_VIOLATION → record_status=PIT_VIOLATION，保留 failure_reason）
Duplicate guard     PASS   （相同 prediction_id → DuplicatePredictionIdError fail closed）
Determinism         PASS   （相同输入两次 dataset_hash 完全一致）
Hash                PASS   （schema/dataset/manifest 三 hash，均不含 created_at）
Manifest            PASS   （10+ 字段完整：version/scope/horizons/counts/versions/hash/builder_version）
```

## 5. Coverage（示例：Golden 2 日 × 2 horizon）

```
expected          = 4
valid             = 4
rejected          = 0
not_available     = 0
pit_violation     = 0
```

（adversarial coverage accounting 已测：PIT_VIOLATION/NOT_AVAILABLE/INVALID 各占 1 时 expected=4/valid=1/pit_violation=1/not_available=1/rejected=1）

## 6. Tests

```
quant_engine   265 passed / 0 failed   （240 既有 + 25 新增）
TradingAgents  1001 passed + 91 subtests, 5 skipped / 0 failed
```

## 7. Acceptance Gates（A–X）

```
A  PredictionRecord contract frozen   PASS
B  prediction_id deterministic        PASS  （sha256，无 random/datetime.now）
C  P5 probability exact-source        PASS
D  horizon contract exact             PASS  （T+1/T+2 各独立 record）
E  future outcome 完全排除            PASS
F  Builder 不重新计算 Quant Engine    PASS  （只 validate/extract/serialize）
G  Builder 不读取未来 market data     PASS  （签名只收 HistoricalRunResult）
H  PIT_VIOLATION fail-closed          PASS
I  NOT_AVAILABLE 显式保留             PASS  （failure_reason 记录）
J  duplicate fail-closed              PASS  （DuplicatePredictionIdError）
K  deterministic ordering             PASS
L  canonical serialization            PASS  （Parquet）
M  manifest complete                  PASS
N  schema hash PASS                   PASS
O  dataset hash deterministic         PASS
P  future mutation invariance PASS    PASS  （改 T+1 close→99999，dataset_hash 不变）
Q  outcome-field schema guard PASS    PASS  （FORBIDDEN_OUTCOME_FIELDS 逐字段检查）
R  Golden 2024-06-03 PASS             PASS
S  Golden 2020-03-16 PASS             PASS
T  coverage accounting PASS           PASS
U  full regression PASS               PASS  （265 + 1001）
V  prediction metrics NOT RUN         PASS  （未计算）
W  trading performance NOT RUN        PASS  （未计算）
X  historical Multi-Agent batch NOT RUN  PASS（未跑）
```

## 8. 明确 NOT RUN

```
Prediction metrics       NOT RUN   （Log Loss/Brier/Accuracy/Directional Accuracy）
Historical Multi-Agent   NOT RUN   （未调用 DeepSeek/TradingAgents）
Trading performance      NOT RUN
```

## 9. LOCK

```
STEP 6.3 = PASS / LOCK
```

关键边界达成：Prediction Dataset 只记录 T 时刻预测信息（P5 概率 + identity + status），
outcome 完全排除，Builder 不重算 Quant Engine、不读未来数据、fail-closed 处理 PIT/duplicate。
下一步为 STEP 6.4（OOS Leakage Audit），等待指令。
