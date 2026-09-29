# SPY Quant Decision System — 落地方案（ROADMAP）

> 目标：数据驱动、可回测、可解释、可验证的 SPY 短期（2 天）方向量化决策系统，服务垂直价差交易。
> 原则：EXTEND > MODIFY > REWRITE。Quant Engine 独立于 TradingAgents，通过 Quant State 接口对接。
> ⚠️ **接口契约（Pydantic schema / 数据流 / 测试 / 验收）以 SPEC.md 为准**；本文件是各阶段任务单。
> 纪律：LLM 只解释，量化确定性计算是唯一事实源；point-in-time 贯穿全程；无样本外验证不进交易。

---

## 修订后阶段（P0~P11）

| 阶段 | 做什么 | 验收（见 ACCEPTANCE_CRITERIA.md） |
|---|---|---|
| P0 | TradingAgents 审计 | ✅ 完成（AUDIT.md） |
| P0.5 | 架构规格书 | ✅ 完成（8 文档） |
| P1 | 数据层 + PIT 契约（四时间字段 + Adapter，复用 TA PIT） | 抽样核对无泄漏 |
| P2 | Feature Engine + Registry | 指标可复现 + 版本化 |
| P3 | Label + Dataset Builder（新增前置） | 阈值全程一致 + 无重叠泄漏 |
| P4 | Event Study + Similarity（去重/最小样本/证据不足） | n≥30 才输出概率 |
| P5 | Regime（多维）+ Probability | 样本外 AUC>0.5 |
| P6 | Calibration | reliability 接近对角线 + Brier 达标 |
| P7 | QuantState（强类型）注入 TradingAgents | 注入后 graph 跑通 + LLM 不篡改 |
| P8 | Decision（Prediction/Trade 分离）+ Risk + Options | 风控否决权不可绕过 |
| P9 | Unified Backtest + Walk Forward（四层） | 四层齐全 + D 不差于 C |
| P10 | Paper Trading（工程验收 + 策略验收分开） | 对账一致 + 不显著偏离样本外 |
| P11 | Execution（人工确认 → 小资金自动 → 全自动） | 分阶段放行 |

## 关键依赖

- **日内预测（30m/1h）**：依赖 OpenD 日内数据就绪，P1~P4 先用日线（次日+2 交易日）做 MVP，不做"日线模拟日内"。
- **期权历史链（P8 期权回测）**：依赖 OpenD，未就绪前 P8 冻结为设计。
- **Breadth/Gamma（P5 Regime 输入）**：无 10 年历史，第一版只用 Trend/VIX/Yield/Volatility。

---

> Quant State 完整 schema 见 QUANT_STATE_SCHEMA.md。

## 每次 Milestone 交付清单（固定格式）

1. 改了哪些文件 + 为什么
2. 新增哪些代码
3. 测试了哪些内容 + 结果
4. 已知问题
5. 下一阶段依赖什么

---

## 下一步

P0 ✅、P0.5 ✅、P1(Layer1 Raw) ✅。下一步 = P1 升级（Data Contract + PIT 四时间字段 + Quant Data Adapter）。三决策默认值见 OPEN_QUESTIONS.md。
