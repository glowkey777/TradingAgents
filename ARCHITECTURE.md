# ARCHITECTURE.md — 整体架构（总纲）

> 本文件是总纲。接口契约细节见各子文档：
> DATA_CONTRACT.md（数据/PIT）、QUANT_STATE_SCHEMA.md（QuantState）、DECISION_RISK_CONTRACT.md（预测/交易/风控/订单）、BACKTEST_DESIGN.md（回测）、ACCEPTANCE_CRITERIA.md（验收）、OPEN_QUESTIONS.md（待决）。审计见 AUDIT.md，阶段任务见 ROADMAP.md。

## 1. 分层与数据流

```
Raw Data ──→ PIT Data Layer ──→ Quant Data Adapter（复用 TA PIT）
                                     ↓
        Quant Engine（features/event_study/regime/probability/calibration）
                                     ↓
        QuantState（强类型 Pydantic）→ Validator → Prompt Renderer
                                     ↓
        TradingAgents（LLM 多 Agent，消费 QuantState，只解释不篡改数值）
                                     ↓
        Decision Engine（Prediction → EV → TradeSignal）
                                     ↓
        Risk Engine（validate_trade → APPROVE/REDUCE/REJECT）
                                     ↓
        Unified Backtest（四层：A Quant / B TA / C Quant+LLM / D +Risk）
```

## 2. 核心不变量（最高优先级，任何开发不可违反）

1. Quant Engine 是基础设施，**不是** Analyst。
2. LLM 永不能改写 Quant 数值（有异见记 llm_assessment，走 Fusion Engine）。
3. Prediction ≠ TradeDecision（中间隔 EV + Risk）。
4. 无校准的预测概率不进下游。
5. 无 walk-forward 样本外验证不进交易。
6. EXTEND > MODIFY > REWRITE（不重写 TradingAgents，只加字段 + 注入点）。

## 3. 修订后 Roadmap

```
P0   审计 ✅（AUDIT.md）
P0.5 架构规格 ✅（本目录 8 文档）
P1   数据层 + PIT 契约（四时间字段 + Adapter）
P2   Feature Engine + Registry
P3   Label + Dataset Builder（新增前置子阶段）
P4   Event Study + Similarity（去重/最小样本/证据不足）
P5   Regime（多维）+ Probability
P6   Calibration
P7   QuantState（强类型）注入 TradingAgents
P8   Decision（Prediction/Trade 分离）+ Risk + Options
P9   Unified Backtest + Walk Forward
P10  Paper Trading（工程验收 + 策略验收分开）
P11  Execution（人工确认 → 小资金自动 → 全自动）
```

Options（IV/Greeks/GEX）若以 SPY 期权为核心，在 P6~P8 之间提前设计接口（见 OPEN_QUESTIONS）。

## 4. 目录结构

```
TradingAgents/
├── tradingagents/            # 官方 v0.5.1，核心零改动
├── quant_engine/             # 新增量化引擎
│   ├── schemas/              # Pydantic（QuantState/Prediction/Trade/Risk）
│   ├── data/                 # raw / pit / adapter / contract
│   ├── features/             # registry + indicators
│   ├── labels/               # builder
│   ├── event_study/          # similarity
│   ├── regime/               # 多维
│   ├── probability/          # model + calibration
│   ├── decision/             # engine + fusion
│   ├── risk/                 # engine
│   ├── backtest/             # unified
│   └── tests/
├── AUDIT.md · SPEC.md · ARCHITECTURE.md · DATA_CONTRACT.md
├── QUANT_STATE_SCHEMA.md · DECISION_RISK_CONTRACT.md
├── BACKTEST_DESIGN.md · ACCEPTANCE_CRITERIA.md · OPEN_QUESTIONS.md
└── ROADMAP.md
```
