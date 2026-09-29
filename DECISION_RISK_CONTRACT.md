# DECISION_RISK_CONTRACT.md — 预测/交易/风控/订单 接口

> 四个不同对象，严格分离。决策链：Prediction → ExpectedValue → TradeSignal → RiskDecision → Order。

## 1. Prediction（市场会怎么走）

```python
class Prediction(BaseModel):
    symbol: str
    horizon: str              # "next_day" | "2d"
    probability_up: float
    probability_flat: float
    probability_down: float
    expected_return: float    # 标的收益，小数
    expected_volatility: float
    calibrated: bool = True   # 未经校准的预测不得进入下游
```

## 2. TradeSignal（值不值得做、做什么）

```python
class TradeSignal(BaseModel):
    prediction_id: str
    strategy: str             # 仅限 Strategy Library
    direction: str            # BULLISH / BEARISH / NEUTRAL
    expected_value: float     # EV，可能为负 → 下游否决
    risk_reward: float
    invalidation: str         # 失效条件（如 "SPY reclaim 775 with VIX falling"）
```

## 3. RiskDecision（风控裁决，有否决权）

```python
class RiskDecision(BaseModel):
    verdict: str              # APPROVE / REDUCE / REJECT
    max_position: float       # 上限仓位（组合占比）
    max_loss: float           # 上限亏损（账户净值比例）
    stop_loss: float
    reasons: list[str]        # 拒绝/缩减的理由

class RiskEngine:
    def validate_trade(self, signal, portfolio, market_state) -> RiskDecision:
        """Trader 提出的任何交易必须过这里。LLM 不得绕过。"""
```

**不变量**：`RiskDecision.verdict != APPROVE` 的交易，不得进入回测成交/模拟/执行。

## 4. Order（执行对象，仅 P11 之后）

```python
class Order(BaseModel):
    side: str                 # BUY/SELL
    legs: list[OrderLeg]      # 垂直价差两腿
    quantity: int
    price_limit: float        # 限价，不擅自改价追单
    gtc: str                  # 有效指令
```

## 5. 决策链（预测 ≠ 交易）

```
QuantState → Probability → Prediction（市场怎么走）
                          ↓
                    Expected Value（P(win)·avg_win − P(loss)·avg_loss）
                          ↓
                    TradeSignal（值不值得、什么策略）
                          ↓
                    RiskDecision（APPROVE / REDUCE / REJECT）
                          ↓
                    Order（P11 后才接执行）
```

**关键**：预测正确（P(up)=60%）但 EV 为负（涨 +0.3% 但最大亏 -3%）→ `NO_TRADE`。两者不混。

## 6. Fusion Engine（LLM 意见与 Quant 数值）

Quant 算 `P(up)=0.637`，LLM 判断"突发新闻削弱概率"，**不能改 0.637**。记录：

```json
{
  "quant_probability": 0.637,
  "llm_assessment": 0.55,
  "fused_probability": null,
  "fusion_method": "weighted"   // 由 Fusion Engine 明确计算，不在 prompt 里让 LLM 自己算
}
```
