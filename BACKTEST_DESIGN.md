# BACKTEST_DESIGN.md — 回测架构、成交假设、对照实验

> 关键：SPY 方向预测准确 ≠ Bull Put Spread 盈利。两种评估分开。

## 1. 两种评估，能力不同

| 评估 | 回答 | 用什么 |
|---|---|---|
| **模型评估**（Quant Engine） | 概率/预期收益/Regime/EventStudy 有没有样本外预测力 | walk-forward + calibration + Brier/AUC |
| **统一交易回测**（策略） | 信号变真实交易后，扣成本/滑点，最终赚不赚、风险可不可接受 | 组合模拟器（自建） |

**不能混指标**：方向 AUC 高 ≠ 价差策略正收益。两层分别验证。

## 2. TradingAgents `backtest.py` 盘点（已读源码，v0.5.1）

- `run_backtest(tickers, dates, config)`：对 (ticker, date) 网格逐个跑 `graph.propagate()`，记录 5 级 rating。
- `summarize()`：按 rating 算 **hit_rate**（方向命中）+ **mean_alpha**（决策后 holding 窗口内 vs benchmark 的超额）。
- **本质是「决策质量评分」，不是组合模拟器** —— docstring 明说 "not a portfolio simulator, must not grow one"。没有成交价、手续费、滑点、仓位、现金账本。

**结论**：`backtest.py` 可复用于**模型/决策方向评估**（对照 B、C 层的"LLM 决策方向准不准"）；但**组合层面的 D 层回测必须自建模拟器**（含仓位/成本/保证金/损益），不往 `backtest.py` 里塞。

## 3. 四层对照实验（统一模拟器跑，同一成本假设）

| 层 | 内容 | 回答 |
|---|---|---|
| A | Quant → Signal → Return | Quant 有没有 alpha |
| B | TradingAgents → Decision → Return | LLM 有没有增益 |
| C | QuantState → TA → Decision → Return | LLM 真用了 QuantState 吗 |
| D | A/C + Risk + Portfolio | 风险调整后收益，风控有没有在起作用 |

**D 层验收**：D 的 Sharpe/MaxDD 不得差于 C 裸信号（否则说明风控在漏/过度交易）。

## 4. 成交假设与成本（第一版定死，别美化）

- 成交价：信号次日**开盘价**成交（不做"当日收盘价成交"的乐观假设）。
- 滑点：SPY 期权 1 腿 $0.05~$0.10/合约；标的 0.05%。
- 手续费：按富途美股期权实际费率（$0.65/腿 + 规费），第一版取保守上界。
- 保证金：垂直价差按**完整宽度**占用（富途实际按 $5×100=$500/张收，非最大亏损——见 memory）。
- 数据可用性：只能用 `available_at <= 决策时点` 的数据。

## 5. 期权价差回测的数据需求（P8 之后，需 OpenD）

标的预测回测 ≠ 期权策略回测。垂直价差真实回测需：

- 历史期权链（各到期日/行权价）
- 买卖报价（bid/ask）历史
- 合约乘数、到期日、行权价
- 成交与退出规则（到期平仓/提前平仓/失效）

**当前缺口**：OpenD 未连上，历史期权链不可得（yfinance 只有近期）。→ 策略回测 P8 前**先冻结为设计**，P8 拿到 OpenD 数据后再实现；P1~P7 只做标的预测 + 决策质量验证。

## 6. 时间切分铁律

1. 严格按时间切，未来数据不进特征/训练/参数选择。
2. 按任务分别评估（方向分类 / 收益回归 / 概率校准 / 期权策略盈利，各算各的指标）。
3. 保留最终未触碰的测试集；一旦按测试集调参，它就不再独立。
4. 检查模型在不同波动/趋势/宏观环境的稳定性，不只报总 AUC。
