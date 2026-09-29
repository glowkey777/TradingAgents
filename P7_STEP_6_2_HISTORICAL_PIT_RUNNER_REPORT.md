# P7 STEP 6.2 — Historical PIT Runner

**STATUS: PASS / LOCK**

---

## 1. 目标

实现历史 Point-in-Time（PIT）运行器：给定历史交易日 T，严格按当时可获得信息重建
QuantState(T) → QuantContext(T)。本阶段只证明「历史 T 可被 PIT-safe、deterministic 重建」，
不运行历史 Multi-Agent、不生成 dataset、不计算指标/收益、不碰 options/position sizing/Kelly。

## 2. Implementation

```
新增 quant_engine/oos/pit_runner.py   核心 runner（T → as_of → P1-P6 → QuantState → QuantContext）
新增 quant_engine/oos/pit_guard.py    PIT firewall（pre-ingestion + post-build 双重防线）
新增 quant_engine/oos/run_models.py   HistoricalRunResult / PITAuditRecord / RunStatus / build_run_id
新增 quant_engine/tests/oos/test_pit_guard.py       5 单元测试
新增 quant_engine/tests/oos/test_pit_runner.py      10 测试（Golden + edge cases）
新增 quant_engine/tests/oos/test_pit_invariance.py  4 critical invariance 测试
```

### 关键设计决策
- **prediction_as_of** 严格复用 6.1 frozen：`resolve_prediction_as_of(T) = T 日 23:59:59`
  （与 P1 `available_at` 语义一致，naive datetime）。
- **不绕过 P1 PIT layer**：runner 直接调用 `build_quant_state(symbol, as_of)`（内部 `load_wide` 已做
  `available_at <= as_of` 钳制），不 `read_csv` / `yfinance.download` 重造第二套读取逻辑。
- **run_id deterministic**：`symbol + prediction_date + horizon + oos-contract-version`，
  无 `datetime.now()` / random UUID。
- **INVALID_TRADING_DATE 不 silent fallback**：T 非交易日直接返回，不自动前/后找日期。

## 3. Golden

```
2024-06-03  PASS   P5 T1 UP=0.3210/FLAT=0.4314/DOWN=0.2476（frozen 一致）
                   P4 bull_trend=0.8333 / low_volatility=1.0（frozen 一致）
2020-03-16  PASS   P4 bear_trend=0.8 / high_volatility>=0.5（COVID 崩盘，frozen 一致）
```

## 4. PIT

```
Pre-ingestion   PASS   audit_pit_df 统计 future/revision 行 + max_available_at（<= as_of）
Post-build      PASS   QuantState trading_date 不晚于 prediction_date
Future mutation PASS   修改 T+1/T+2 close → QuantState(T).market 完全不变
Revision mutation PASS  修改 revision_time > as_of 数据 → QuantState(T) 完全不变
```

**PIT invariance 核心证据**：future mutation 测试把 T+1 之后的 close 改成 99999.0，重新运行
`run_historical_t(2024-06-03)`，`quant_state["market"]` 与 baseline 逐字段相等（as_of 钳制隔离了未来数据）。

## 5. Determinism

```
PASS：相同输入两次运行，quant_state / quant_context / p4_regime / p5_probability /
source_lineage / quant_state_version / run_id 完全一致。
created_at 来自 as_of 语义（quant_state["as_of"] == "2024-06-03..."），非 wall-clock。
```

## 6. Tests

```
quant_engine   240 passed / 0 failed   （221 既有 + 19 新增 PIT）
TradingAgents  1001 passed + 91 subtests, 5 skipped / 0 failed
```

## 7. Acceptance Gates（A–Q）

```
A  Historical T 定义正确           PASS  （非交易日 → INVALID_TRADING_DATE）
B  prediction_as_of 严格复用 6.1   PASS  （resolve_prediction_as_of 单一来源）
C  PIT firewall 存在               PASS  （pit_guard.py，双重防线）
D  available_at boundary 正确      PASS  （<= as_of ALLOW，+epsilon REJECT）
E  revision boundary 正确          PASS  （revision_time > as_of → REJECT）
F  不绕过 P1 PIT layer             PASS  （无 read_csv / yfinance 重造）
G  warm-up PIT-safe                PASS  （feature lookback 全在 as_of 钳制内）
H  QuantState 不读取未来数据       PASS  （trading_date == T）
I  future mutation invariance      PASS
J  revision mutation invariance    PASS
K  deterministic run               PASS
L  Golden 2024-06-03               PASS
M  Golden 2020-03-16               PASS
N  edge cases                      PASS  （周末/假日/月初末/宏观日/revision/cutoff边界）
O  machine-readable PIT audit      PASS  （PITAuditRecord 7 字段，非单 bool）
P  regression                      PASS  （240 + 1001）
Q  无历史批量/指标/交易评估        PASS  （NOT RUN）
```

## 8. Edge Cases 覆盖

```
Case A 正常交易日   PASS
Case B 周末        PASS  （INVALID_TRADING_DATE）
Case C 市场假日    PASS  （INVALID_TRADING_DATE，2024-07-04）
Case D 月初/月末   PASS
Case E 宏观发布日  PASS
Case F revision    PASS  （guard 单元 + revision mutation invariance）
Case G cutoff 边界 PASS  （== as_of ALLOW，== as_of + epsilon REJECT）
```

## 9. 明确 NOT RUN

```
Historical batch      NOT RUN
Prediction metrics    NOT RUN
Trading performance   NOT RUN
```

## 10. LOCK

```
STEP 6.2 = PASS / LOCK
```

成功标准达成：历史 T 的 QuantState 能被严格、可重复、无未来信息污染地重建。
下一步为 STEP 6.3（Prediction Dataset），等待指令。
