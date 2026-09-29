# ACCEPTANCE_CRITERIA.md — 各阶段验收标准

> 每阶段必须有：可执行验收条件、基准模型、测试区间、失败处理规则。阈值结合样本量与成本，不凭空定通用标准。

## 通用规则

- 确定性：同一输入同一输出（pytest 复现测试）。
- 失败处理：验收不过 → 回到该阶段修，不带着问题进下一阶段。
- 任何"达标"必须给出对比基准（无基准 = 没达标）。

## 各阶段验收

### P1 数据层 + PIT 契约
- **验收**：任抽 10 条样本手工核对「available_at 正确、无未来数据泄漏」。
- **基准**：SPY/宏观多源对齐后，日线收盘价与 yfinance 原始一致（偏差=0）。
- **失败**：发现任何 `available_at > as_of` 却出现在回测数据里的记录 → P1 不通过。

### P2 Feature Engine + Registry
- **验收**：每个 feature 有 registry 条目（公式/输入/频率/版本/可用时间）+ 单测。
- **基准**：RSI/ATR/MA 与 `pandas-ta` 或手算值一致（容许 1e-6）。
- **失败**：feature 无版本号或无单测 → 不通过。

### P3 Label + Dataset Builder
- **验收**：Label 边界（UP/FLAT/DOWN）在 train/valid/test 全程一致；时间切分无重叠样本。
- **基准**：三分类历史分布接近均匀（不出现 90% 一类）。
- **失败**：测试集样本出现在训练特征里（leakage）→ 不通过。

### P4 Event Study + Similarity
- **验收**：样本去重（重叠事件不重复计）、最小样本量阈值、`n < 阈值` 时返回「证据不足」而非强行输出概率。
- **基准**：`evidence="sufficient"` 的样本量 ≥ 30（用户回测铁律）。
- **失败**：重叠窗口重复计入同一段行情 → 不通过。

### P5 Regime（多维）+ Probability
- **验收**：Regime 四维各自输出概率分布（和为 1）；概率模型有简单基准对比。
- **基准**：XGBoost 概率 vs 历史无条件频率（dummy）——AUC 必须显著 > 0.5，且样本外不塌。
- **失败**：样本外 AUC ≤ 0.5 或明显塌陷 → 模型砍掉，不进入下游。

### P6 Calibration
- **验收**：reliability curve 接近对角线；Brier 低于无条件基准。
- **基准**：预测 P=70% 时实际频率落在 65%~75%（校准误差 < 5%）。
- **失败**：校准不合格 → 概率不进入 QuantState。

### P7 QuantState 注入
- **验收**：`QuantStateValidator` 通过才注入；`TradingAgentsGraph.propagate()` 带 QuantState 仍跑通（复用 tests/test_backtest.py 模式）。
- **失败**：LLM 改写 Quant 数值（抽查 prompt 与 state 不一致）→ 不通过。

### P8 Prediction/Trade 分离 + Risk
- **验收**：Prediction 和 TradeDecision 是两个对象；任何 TradeSignal 必经 `RiskEngine.validate_trade`。
- **失败**：RiskDecision 未 APPROVE 的交易进了回测成交 → 不通过。

### P9 Unified Backtest + Walk Forward
- **验收**：四层结果齐全；walk-forward 滚动窗口样本外有效；D 层（含风控）不差于 C 裸信号。
- **基准**：回测收益必须扣手续费+滑点+保证金占用，报 Sharpe/Sortino/MaxDD/Calmar。
- **失败**：仅靠测试集调参刷高收益 → 不采信，作废重来。

### P10 Paper Trading（放行分两类，不只看赚钱）
- **工程验收**：数据正常、无重复订单、无状态错乱、风险限制生效、订单与持仓可对账。
- **策略验收**：观察窗口内积累足够有效交易样本，扣成本滑点后不显著偏离样本外回测，满足风险要求。
- **失败**：Paper 赚钱但工程验收不过（对不上账）→ 不放行全自动。

## 全自动放行门槛（P11 之后）

Paper Trading 通过 + 工程验收通过 + 策略验收通过 + 用户确认，才逐步从「人工确认」→「小资金自动」→「全自动」。绝不因 Paper 短期赚钱直接上全自动。
