# P7_PRECHECK.md — TradingAgents v0.5.1 架构审计

> 基于实际代码（非 Prompt 猜测）。审计对象：`TradingAgents/tradingagents/`（v0.5.1，git @35543d0）。

## 结论：P7 最小接入点已确定，无需重构 TradingAgents。

---

## Q1. TradingAgents 当前 State / Graph State 是什么？

**`AgentState(MessagesState)`**（`agents/state.py`），LangGraph TypedDict，扩展 MessagesState。

字段全为字符串（report 是自然语言文本）：

```python
class AgentState(MessagesState):
    company_of_interest: str
    asset_type: str
    instrument_context: str      # 确定性 ticker identity，run start 注入
    trade_date: str

    market_report / sentiment_report / news_report / fundamentals_report: str

    investment_debate_state: InvestDebateState   # bull/bear/history/judge_decision/count
    investment_plan: str
    trader_investment_plan: str

    risk_debate_state: RiskDebateState           # aggressive/conservative/neutral/history/judge
    final_trade_decision: str

    past_context: str             # 记忆层，run start 注入
    portfolio_context: str        # caller 持仓，run start 注入
```

关键：**没有量化字段，全是 prose 文本**。`InvestDebateState` / `RiskDebateState` 是嵌套 TypedDict（bull_history/bear_history/history/current_response/judge_decision/count）。

## Q2. Graph 如何组织？

LangGraph `StateGraph(AgentState)`（`graph/setup.py`），线性链 + 两个辩论循环：

```text
START
  → Market Analyst（agent→tool→clear）
  → Social/Sentiment Analyst
  → News Analyst
  → Fundamentals Analyst
  → Bull Researcher ⇄ Bear Researcher（条件边 DEBATE_PATH_MAP）
  → Research Manager（deep LLM，输出 ResearchPlan）
  → Trader（输出 TraderProposal）
  → Aggressive ⇄ Conservative ⇄ Neutral Analyst（条件边 RISK_ANALYSIS_PATH_MAP）
  → Portfolio Manager（deep LLM，输出 PortfolioDecision）
  → END
```

入口：`TradingAgentsGraph.propagate(company_name, trade_date, asset_type, portfolio)`。
结构化输出：ResearchPlan / TraderProposal / PortfolioDecision / SentimentReport（`agents/schemas.py`，Pydantic）。

## Q3. Agent 如何共享 context？

通过 **AgentState 的字符串字段**：
- `instrument_context` / `past_context` / `portfolio_context` 在 `create_run_state()` → `Propagator.create_initial_state()` 一次性构建注入。
- 各 agent 从 `state["..."]` 读取（`agents/context.py` 的 `get_instrument_context_from_state` 等）。
- 报告字段（market_report 等）在 graph 中传递，供下游 agent 阅读。

## Q4. 当前 data tools 是什么？

`agents/tools.py`，全部用 `InjectedState("trade_date")` + `dataflows/date_window.py` 的 `as_of`/`as_of_window` 做 **PIT 约束**（任何日期请求都被钳制到 trade_date）：

| Tool | 用途 | vendor |
| --- | --- | --- |
| get_stock_data | OHLCV | yfinance |
| get_indicators | 单技术指标（rsi/macd/...） | yfinance |
| get_verified_market_snapshot | 确定性快照（事实真相源） | yfinance |
| get_fundamentals / balance_sheet / cashflow / income | 基本面 | yfinance |
| get_news / get_global_news / get_insider | 新闻 | yfinance |
| get_macro_indicators | 宏观（FRED） | fred |
| get_prediction_markets | 预测市场 | polymarket |

**关键：TradingAgents 已有 PIT 机制（date_window.as_of），且 tool 永不服务 trade_date 之后的数据。**

## Q5. QuantState 最小接入点在哪里？

**`create_run_state()` → `Propagator.create_initial_state()` 的 context 注入层。**

现有 `instrument_context` / `past_context` / `portfolio_context` 三个 caller-supplied 字符串，在 run start 一次性注入。QuantState 走同一条路径：

```text
QuantState（typed）
    ↓ renderer（deterministic）
quant_context（str，新字段）
    ↓ create_initial_state 注入
AgentState.quant_context
    ↓ market_analyst / bull / bear 的 prompt 消费
```

这是唯一「整个 graph 都可见、且无需改 agent 内部逻辑」的注入点。

## Q6. 哪些模块可以复用？

- `dataflows/date_window.py` — PIT 约束（as_of / as_of_window），**P7 直接复用，不重写**。
- `agents/schemas.py` — 结构化输出模式（ResearchPlan/TraderProposal/PortfolioDecision），TradingThesis 参考其风格。
- `graph/propagation.py` 的 context 注入机制。
- `default_config.py` — config 体系，P7 的 quant_context 开关放这里。

## Q7. 哪些地方需要新增 adapter？

全部新增在 `quant_engine/integration/`（不碰 TradingAgents 核心）：

```text
quant_engine/integration/
├── context.py                # TradingAgentsQuantContext（typed，引用 QuantState）
├── renderer.py               # QuantState → deterministic LLM-readable text（versioned）
├── thesis.py                 # TradingThesis 强类型（directional_bias + evidence）
├── provenance.py             # LLM provenance（model/provider/temperature/prompt_version）
├── tradingagents_adapter.py  # QuantState → quant_context 注入
└── pipeline.py               # 标准 run 入口
```

TradingAgents 侧的**最小 additive 修改**（2 处，均为可选字段 + 默认值，不破坏现有行为）：
1. `agents/state.py`：`AgentState` 加 `quant_context: str` 字段。
2. `graph/propagation.py`：`create_initial_state` 加 `quant_context: str = ""` 参数。

（第 3 处可选：market_analyst + bull/bear researcher 的 prompt 里加 `{quant_context}` 变量。）

## Q8. 为什么这是最小侵入式方案？

1. **不改 graph 结构、不改任何 agent 逻辑、不改 tool、不改 vendor。**
2. 复用 TradingAgents 已有的「run-start context 注入」机制（instrument/past/portfolio 三个字段先例）。
3. QuantState 只以「渲染文本」形式进入 AgentState 的一个新字符串字段，语义与现有 report 字段一致。
4. TradingThesis 作为**独立输出 Contract**（在 quant_engine/integration/ 里），不替换 TradingAgents 现有的 final_trade_decision。
5. 未来换 P5 Model A→B→D、加 ML/Gamma/IV/Breadth，只改 renderer，TradingAgents 零改动。

## 边界确认（P7 硬约束）

- QuantState 是唯一 Quant Engine → Agent 边界；TradingAgents 不直接读 P1-P5。
- LLM 不修改 QuantState（agent 输出是新 artifact，不是新 QuantState）。
- 文本只是 presentation，source of truth 是 typed QuantState。
- Agent 不得伪造 IV/Gamma/Breadth/Risk（QuantState 里 NOT_AVAILABLE 就写 NOT_AVAILABLE）。
- P7 测试全 offline，用 MockLLM，不依赖真实 LLM/网络。
