# Phase 0.5 — Quant System Architecture Specification（架构规格书）

> 本文件是 P1 之前的**接口契约**。所有 Python class / Pydantic schema / 数据流 / 测试标准 / 验收条件在此定义。
> 原则不变：EXTEND > MODIFY > REWRITE；LLM 不碰量化数值；point-in-time 贯穿；无校准/样本外验证不进交易。

---

## 0. 核心不变量（写入工程规则，最高优先级）

1. **Quant Engine 是基础设施，不是 Agent** —— 它不参与 LLM 讨论，只产出 `QuantState` 供所有 Agent 消费。
2. **LLM 永不能改写 Quant 数值** —— Quant 算出的 `P(up)=63.7%`，LLM 只能注释，不能改。若 LLM 有不同判断，记录 `llm_assessment` 单独字段，融合走 Fusion Engine，不在 prompt 里让 LLM 自己算。
3. **预测 ≠ 交易** —— Prediction 和 TradeDecision 是两个对象，中间隔着 Expected Value + Risk。
4. **无校准的预测概率不进入下游** —— raw probability 必须过 Calibration 才是 calibrated probability。
5. **任何模型必须过 walk-forward 样本外验证**，否则不进交易。

---

## 1. 数据流总图

```
Raw Data (raw/)                          # Layer 1：原始，如 yfinance 原样
      ↓
PIT Data Layer (pit/)                    # Layer 2：四时间字段标准化
      ↓                                    observation / release / available / revision
Quant Data Adapter (data/adapter.py)     # Layer 3：复用 TradingAgents PIT 纪律
      ↓                                    (date_window.py)，不重造 PIT
┌─────────────────────────────────────┐
│          Quant Engine               │
│  Features(registry) → Labels        │
│  EventStudy(similarity) → Regime    │
│  Probability → Calibration          │
└──────────────────┬──────────────────┘
                   ↓
            QuantState (Pydantic)       # 强类型，非 str
                   ↓
         QuantStateValidator           # schema 校验 + 数值不变量校验
                   ↓
         Agent Prompt Renderer         # 按 Agent 需求渲染字段
                   ↓
            TradingAgents               # LLM 多 Agent（消费 QuantState）
                   ↓
         Decision Engine                # Prediction → EV → Trade Signal
                   ↓
         Risk Engine                    # validate_trade → APPROVE/REDUCE/REJECT
                   ↓
         Unified Backtest               # 四层回测（见 §9）
```

---

## 2. 目录结构（quant_engine/ 完整版）

```
TradingAgents/quant_engine/
├── schemas/                 # Pydantic schema（契约，先于实现）
│   ├── quant_state.py       # QuantState 总对象
│   ├── states.py            # instrument/technical/macro/regime/probability/event_study/options/risk 各 State
│   ├── prediction.py        # Prediction 对象
│   ├── trade.py             # TradeDecision 对象
│   ├── risk.py              # RiskDecision 对象
│   └── metadata.py          # QuantMetadata + 版本对象
├── data/
│   ├── raw/                 # Layer 1 原始数据（spy_macro CSV 归这里）
│   ├── pit/                 # Layer 2 PIT 标准化（四时间字段）
│   ├── adapter.py           # Layer 3 Quant Data Adapter
│   └── contract.py          # Data Contract（字段/单位/频率/可用性规则）
├── features/
│   ├── registry.py          # Feature Registry（版本化）
│   └── indicators.py        # 指标实现（RSI/ATR/MA/波动率...）
├── labels/
│   └── builder.py           # Label + Dataset Builder（三分类 + 动态阈值）
├── event_study/
│   └── similarity.py        # Similarity / Event Study Engine
├── regime/
│   └── engine.py            # Regime 概率化
├── probability/
│   ├── model.py             # LR/RF/XGBoost
│   └── calibration.py       # Platt/Isotonic + Brier + reliability
├── decision/
│   ├── engine.py            # Prediction → EV → Trade Signal
│   └── fusion.py            # Fusion Engine（quant vs llm_assessment）
├── risk/
│   └── engine.py            # RiskEngine.validate_trade
├── backtest/
│   └── unified.py           # Unified Backtest（四层）
└── tests/
```

---

## 3. 🔴 QuantState（强类型，替代 `quant_context: str`）

```python
from pydantic import BaseModel, Field
from datetime import datetime

class QuantState(BaseModel):
    schema_version: str                    # "1.0"
    as_of: datetime                        # 本状态对应的时点（PIT 关键）

    instrument: InstrumentState
    technical: TechnicalState
    macro: MacroState
    regime: RegimeState
    probability: ProbabilityState          # 已校准
    event_study: EventStudyState
    options: OptionsState | None = None    # 期权层，P5/P6 后才填充
    risk: RiskState
    metadata: QuantMetadata
```

**注入方式**：`AgentState` 加 `quant_state: QuantState | None`（不是 str）。
`create_run_state()` 注入 QuantState 对象；`Agent Prompt Renderer` 按每个 Agent 需求把 QuantState 渲染成 prompt 片段（Markdown），而不是把整个对象塞给 LLM。

**校验**：`QuantStateValidator` 断言——概率 ∈[0,1] 且三分类和为 1、expected_return 有对应 volatility、as_of 不晚于今天、版本号匹配。校验失败则拒绝注入，不静默。

---

## 4. 🔴 Data Contract + 三层数据架构

### 4.1 三层

| 层 | 目录 | 内容 | 谁维护 |
|---|---|---|---|
| Layer 1 Raw | `data/raw/` | 原始 vendor 数据，不做任何加工 | fetch_data.py |
| Layer 2 PIT | `data/pit/` | 四时间字段标准化后的数据 | pit 模块 |
| Layer 3 Adapter | `data/adapter.py` | 按 as_of 返回「当时可见」的数据视图 | Quant Engine 调用 |

**关键决策**：Quant Engine **不重造 PIT**。TradingAgents 的 `dataflows/date_window.py` 已是 PIT 基础设施，Adapter 复用它。数据只有一套源头，避免「同一个 SPY 两个系统两个价」。

### 4.2 PIT 四时间字段（替代单一 available_at）

```python
class DataPoint(BaseModel):
    symbol: str
    field: str
    value: float
    observation_time: datetime   # 数据「发生/观测」时点（如 CPI 反映的月份）
    release_time: datetime       # 官方发布时间（如 CPI 08:30 发布）
    available_time: datetime     # 真正可用 = max(release, 采集延迟)
    revision_time: datetime | None  # 被修正的时间（如 GDP 二次修正）
```

**回测取数规则**：`as_of = "2026-08-11"` 时，只有 `available_time <= as_of` 且 `revision_time is None or revision_time > as_of` 的数据可见。即「2026-08-12 08:30 发布的 8 月 CPI，在 8-11 那天的回测里不存在」。

---

## 5. 🔴 Label + Dataset Builder（Probability 的前置）

### 5.1 三分类标签（动态阈值，不用固定 %）

```python
# horizon ∈ {30m, 1h, close, next_day, 2d}
# 阈值基于当期 ATR 动态化，避免高波动/低波动期阈值失真
UP   : return >  +0.25 × ATR(horizon)
DOWN : return <  -0.25 × ATR(horizon)
FLAT : 其余
```

第一版固定阈值仅作 30m 兜底（`>+0.15%` / `<-0.15%`），1h 及以上一律 ATR 动态阈值。

### 5.2 Dataset Builder

```python
class DatasetBuilder:
    def build(self, as_of_dates, horizon) -> Dataset:
        """每条样本 = (features@t, label@t+horizon)，
        严格只用 available_time <= t 的数据，标签只用 t+horizon 之后已实现数据。"""
```

**验收**：任取一条样本，手工核对「特征在 t 时刻可见、标签是 t+horizon 的真实结果」，无未来数据泄漏。

---

## 6. 🔴 Probability Calibration（假量化的分水岭）

```python
class Calibrator:
    def fit(self, raw_probs, outcomes) -> Calibrator: ...   # Platt / Isotonic
    def calibrate(self, raw_prob) -> float: ...

class CalibrationReport(BaseModel):
    raw_probability: float
    calibrated_probability: float
    brier_score: float
    reliability_curve: list[tuple[float, float]]   # (预测桶, 实际频率)
    n_samples: int
```

**验收**：reliability curve 接近对角线（预测 70% 时实际 ≈68%~72%）；Brier score 低于基准（历史无条件概率）。校准不合格的模型，其概率不进 QuantState。

---

## 7. 🔴 Prediction 与 TradeDecision 彻底分离

```python
class Prediction(BaseModel):          # 这是「市场会怎么走」
    symbol: str
    horizon: str                      # "30m" | "1h" | "close" | "1d" | "2d"
    probability_up: float
    probability_flat: float
    probability_down: float
    expected_return: float            # 期望收益
    expected_volatility: float
    calibrated: bool = True

class TradeDecision(BaseModel):       # 这是「值不值得下注、下多少」
    action: str                       # BUY/SELL/NO_TRADE
    strategy: str                     # 仅限 Strategy Library
    position_size: float              # 组合占比
    entry: float
    stop_loss: float
    take_profit: float | None
    expected_value: float             # EV = P(win)·avg_win − P(loss)·avg_loss
    risk_reward: float
    invalidation: str                 # 失效条件
```

**决策链**：`Prediction → ExpectedValue → Risk → TradeDecision`。预测正确但 EV 为负 → `NO_TRADE`。

---

## 8. 🔴 Risk Interface（P1 就定义，P8 实现完整）

```python
class RiskDecision(BaseModel):
    approved: bool                    # True=通过，False=拒绝
    verdict: str                      # APPROVE / REDUCE / REJECT
    max_position: float               # 上限仓位
    max_loss: float                   # 上限亏损
    stop_loss: float
    reasons: list[str] = []

class RiskEngine:
    def validate_trade(self, signal, portfolio, market_state) -> RiskDecision:
        """TradingAgents 提出的交易，必须过这里。Risk 有否决权，Trader 不可绕过。"""
```

**不变量**：任何 TradeDecision 未经 `RiskEngine.validate_trade` 通过，不得进入回测/模拟/执行。

---

## 9. 🔴 Unified Backtest（四层，统一引擎）

```python
class UnifiedBacktestEngine:
    def run_quant_only(self, ...)          # A: Quant→Signal→Return   (Quant 有 alpha 吗)
    def run_agents_only(self, ...)         # B: TA→Decision→Return     (LLM 有增益吗)
    def run_quant_plus_llm(self, ...)      # C: QuantState→TA→Return   (LLM 真用了 QuantState 吗)
    def run_full_system(self, ...)         # D: +Risk+Portfolio        (风险调整后收益)
```

四层输出对比，回答「哪个组件真创造 alpha」。统一使用 TradingAgents 的 `run_backtest` 决策质量评分 + 自建组合模拟器（D 层）。

**验收**：四层结果齐全，且 D 层（含风控）Sharpe/MaxDD 必须不差于 C 层裸信号，否则说明风控在漏。

---

## 10. 🔴 Feature Registry + 版本管理

```python
class FeatureSpec(BaseModel):
    name: str            # "rsi_14"
    version: str         # "1.0"
    lookback: int        # 14
    frequency: str       # "1d"
    source: str          # "SPY"
    availability_rule: str
    formula: str
    created_at: str

class DatasetVersion(BaseModel):
    dataset: str         # "spy_pit_v7"
    feature_set: str     # "feature_set_2026_09_01"
    code_commit: str
    training_period: str

class ModelVersion(BaseModel):
    model: str           # "xgboost_v3"
    feature_version: str
    dataset_version: str
    code_commit: str
```

**规则**：每次训练必须记录 Model + Feature + Dataset + Code Commit + Parameter 五元组，否则回测结果不可复现、不予采信。

---

## 11. 🟡 现在设计、后实现的接口（留好接口位）

- **Regime 概率化**：`RegimeState = {bull_trend, bear_trend, range, high_vol, macro_shock, event_driven}` 软分布，不输出硬标签。
- **Similarity Engine**：当前状态向量 → 历史 Top-N 相似状态 → 未来各 horizon 的 mean/median/std/P(up)/P(down)/max_drawdown/max_runup。
- **Options Interface**：`OptionsState = {iv, iv_rank, term_structure, skew, greeks, gex, gamma_wall, zero_gamma, expected_move}`，P5/P6 填充。
- **Volatility Forecast**、**Portfolio Engine**、**Prediction Journal**、**Model Arena**：接口位预留，不在 P1~P4 实现。

---

## 12. 测试标准 + 验收条件（每 Phase 通用）

1. 每个模块 pytest 单测，**确定性可复现**（同输入同输出）。
2. 数据层：任取样本手工核对 point-in-time 无泄漏。
3. 概率层：calibration 报告达标才放行。
4. 回测：train/validation/test 分离 + walk-forward，显式查 look-ahead/leakage/survivorship/overfitting。
5. 集成：QuantState 注入后 `TradingAgentsGraph.propagate()` 仍跑通（复用 tests/test_backtest.py 模式）。
6. 交付格式：改了哪些文件+为什么 / 新增代码 / 测试结果 / 已知问题 / 下阶段依赖。

---

## 13. 修订后的 Roadmap（替代旧 P0~P11）

```
P0   TradingAgents 审计            ✅ 完成（AUDIT.md）
P0.5 架构规格书                    ✅ 本文件（SPEC.md）
P1   Data Contract + PIT           # 四时间字段 + Adapter（复用 TA PIT）
P2   Feature Engine + Registry     # 指标 + 版本化
P3   Label + Dataset Builder       # 三分类 + 动态阈值
P4   Event Study + Similarity
P5   Regime Engine（概率化）
P6   Probability + Calibration
P7   QuantState（强类型）+ 注入 TradingAgents
P8   Prediction/Trade Decision 分离
P9   Risk Engine
P10  Unified Backtest（四层）
P11  Walk Forward
P12  Options（IV/Greeks/GEX，若以 SPY 期权为核心则提前到 P6~P8 之间设计）
P13  Paper Trading
P14  Execution
```
