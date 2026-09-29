# TradingAgents v0.5.1 审计报告（Phase 0 交付）

审计时间：2026-09-27
仓库：https://github.com/TauricResearch/TradingAgents @ 35543d0（v0.5.1, 2026-09-24 发布）
本地：F:\Youtube\0413\TradingAgents

---

## A. 架构图（分层）

```
                    ┌─────────────────────────────────────┐
                    │           调用入口（CLI / 程序）        │
                    │  cli/run.py · backtest.run_backtest() │
                    └──────────────────┬──────────────────┘
                                       ↓
                    ┌─────────────────────────────────────┐
                    │      Graph 编排层（LangGraph）        │
                    │  trading_graph.py（propagate 主入口）  │
                    │  setup.py（节点接线）                  │
                    │  conditional_logic.py（辩论轮数控制）   │
                    │  propagation.py（初始状态组装）        │
                    │  checkpointer.py（断点续跑 SqliteSaver）│
                    │  reflection.py（决策回看/alpha 结算）   │
                    │  settlement.py（到期决策结算）          │
                    └──────────────────┬──────────────────┘
                                       ↓
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        ↓              ↓               ↓               ↓              ↓
   ┌──────────┐  ┌──────────┐   ┌──────────┐   ┌──────────┐  ┌──────────┐
   │ Market   │  │ News     │   │ Sentiment│   │ Fundamen │  │ Research │
   │ Analyst  │  │ Analyst  │   │ Analyst  │   │ Analyst  │  │ Bull/Bear│
   └────┬─────┘  └────┬─────┘   └────┬─────┘   └────┬─────┘  │ + Manager│
        └──────────────┴──────────────┴──────────────┘        └────┬─────┘
                              ↓                                    ↓
                    ┌──────────────────┐                  ┌──────────────┐
                    │   Research Manager │──investment_plan→│    Trader     │
                    └──────────────────┘                  └──────┬───────┘
                                                                 ↓
                    ┌──────────────────────────────────────────────────┐
                    │  Risk 辩论（aggressive / conservative / neutral） │
                    └──────────────────────────┬───────────────────────┘
                                               ↓
                    ┌──────────────────────────────────────────────────┐
                    │  Portfolio Manager → final_trade_decision        │
                    │  （5 级 rating: Buy/Overweight/Hold/Underweight/Sell）│
                    └──────────────────────────┬───────────────────────┘
                                               ↓
                    ┌──────────────────────────────────────────────────┐
                    │  Decision Log（decision_log.py，point-in-time 记忆）│
                    └──────────────────────────────────────────────────┘
```

**数据层（独立于 graph）**：`dataflows/` → `router.py` → `vendors/`（yahoo / alpha_vantage / fred / polymarket / reddit / sec_edgar / stocktwits），所有工具经 `date_window.py` 做 point-in-time 过滤。

**LLM 层（独立）**：`llm_clients/` → factory + model_catalog，支持 openai / anthropic / azure / bedrock / google / openai-compatible（含 deepseek）。

---

## B. 模块依赖

```
backtest.py ──→ trading_graph.py ──→ graph/setup.py ──→ agents/*（各节点）
trading_graph.py ──→ dataflows/config.py（run_config 上下文）
                  ──→ decision_log.py（记忆）
                  ──→ llm_clients/（deep + quick 两个客户端）
agents/state.py（AgentState = MessagesState 扩展）→ 全 graph 共享
dataflows/date_window.py ← 被所有 vendor 工具引用（point-in-time 统一）
```

---

## C. Capability Matrix（0.5.1 已具备）

| 能力 | 状态 | 位置 |
|---|---|---|
| 4 分析师（market/news/sentiment/fundamentals） | ✅ | agents/analysts/ |
| Bull/Bear 辩论 | ✅ | agents/researchers/ |
| Trader（结构化输出 Buy/Hold/Sell + 进场/止损/仓位） | ✅ | agents/trader/ |
| Risk 三方辩论 | ✅ | agents/risk_mgmt/ |
| Portfolio Manager | ✅ | agents/managers/portfolio_manager.py |
| 历史日期回测 | ✅ | backtest.py（run_backtest + summarize） |
| **Point-in-time 防未来数据** | ✅ | dataflows/date_window.py（in_window/as_of/as_of_window/withhold_live_profile） |
| Checkpoint 断点续跑 | ✅ | graph/checkpointer.py |
| 记忆（决策日志，point-in-time 过滤） | ✅ | decision_log.py |
| 多 LLM provider（含 deepseek） | ✅ | llm_clients/ |
| 结构化输出（structured outputs） | ✅ | agents/structured.py + schemas.py |
| 组合感知（portfolio-aware） | ✅ | portfolio.py + portfolio_context |
| 报告树输出 | ✅ | reporting.py |
| 决策质量回测评分（alpha vs benchmark） | ✅ | backtest.summarize() |

---

## D. 可直接复用模块（不要动）

- **数据层全套**：`dataflows/`（vendors + router + point-in-time），已含 yahoo/fred/polymarket/reddit/sec_edgar/stocktwits
- **Graph 编排**：`graph/`（LangGraph 工作流、checkpoint、结算、回看）
- **LLM Clients**：`llm_clients/`（含 deepseek 兼容）
- **Backtest 引擎**：`backtest.py`（`run_backtest` + `summarize`）
- **Decision Log / 记忆**：`decision_log.py`
- **point-in-time 机制**：`dataflows/date_window.py`（这是整套系统最值钱的 correctness 资产）

---

## E. 需要新增的模块（Quant Engine，独立目录）

```
TradingAgents/quant_engine/
├── data/          # SPY + 宏观数据层（point-in-time schema）
├── features/      # 技术指标（RSI/ATR/MA/VWAP/波动率...）
├── event_study/   # 历史类似条件统计
├── regime/        # 市场状态判断
├── probability/   # 短周期概率预测（LR/RF/XGBoost）
├── schemas/       # Quant State JSON 定义
├── backtest/      # walk-forward + 魔鬼测试
└── tests/
```

---

## F. 需要修改的模块（集成点，最小改动）

1. **State 加一个字段**：`agents/state.py` 的 `AgentState` 加 `quant_context: str`（Quant State JSON 渲染成的字符串）
2. **注入点**：`trading_graph.py` 的 `create_run_state()`，类比 `instrument_context` / `portfolio_context`，新增 `quant_context` 注入
3. **消费点**：`agents/trader/trader.py`（Trader prompt 附加 Quant Context，和 market_report 同位置）、各 analyst 可选
4. **配置**：`default_config.py` 加 quant 相关开关（quant_enabled 等）
5. **holding_period**：`holding_period_days` 默认 5，你的 2 天短线可配 2

> 原则：EXTEND > MODIFY。Quant Engine 是独立目录，TradingAgents 只加一个字段 + 一处注入，核心逻辑零改动。

---

## G. 风险点

1. **LLM 不能作为量化计算的事实源**——概率/希腊字母/仓位/EV 必须由 Quant Engine 确定性算，LLM 只做解释（已在架构上隔离）
2. **point-in-time 必须贯穿 Quant Engine**——你自己的 Event Study / 回测若混入未来数据，整套系统失效。复用 `date_window.py` 的纪律，数据每条带 `available_at`
3. **样本外验证是硬门槛**——无 walk-forward 的预测力证明，一律不进入交易
4. **数据源**：fred 需 FRED_API_KEY（免费申请），macro 数据若缺，regime/probability 输入不完整
5. **LLM 成本**：完整 graph 每次 run 调多个 LLM 节点，回测扫描（多 ticker×多日期）token 消耗大，需控制样本量

---

## H. 测试策略

- Quant Engine 每个模块配 pytest 单测（复现性：同一输入同一输出）
- 回测必须 train/validation/test 分离 + walk-forward，显式查 look-ahead / leakage / survivorship / overfitting
- 集成测试：Quant State 注入后 graph 仍能跑通（复用 tests/test_backtest.py 模式）
- Prediction Journal 校验：预测 vs 实际自动对账

---

## I. Phase Roadmap（见 ROADMAP.md）

P0 审计（✅ 本文件）→ P1 数据层 → P2 特征 → P3 Event Study → P4 Regime → P5 Probability → P6 Quant State 集成 → P7 LLM 辩论接通 → P8 期权+风控 → P9 Walk Forward → P10 Paper Trading → P11 执行
