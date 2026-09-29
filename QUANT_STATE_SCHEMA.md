# QUANT_STATE_SCHEMA.md — QuantState 字段定义与示例

> 强类型 Pydantic，非 str。每个字段的单位、含义、时间戳、缺失状态、版本必须明确。

## 1. 总 Schema

```python
class QuantState(BaseModel):
    schema_version: str          # "1.0"
    as_of: datetime              # 判断对应时点（PIT 关键，= 决策日收盘）
    horizon: str                 # 主预测期限："next_day" | "2d"（日线优先）

    instrument: InstrumentState
    technical: TechnicalState
    macro: MacroState
    regime: RegimeState          # 多维，非互斥
    probability: ProbabilityState
    event_study: EventStudyState
    options: OptionsState | None = None
    risk: RiskState
    data_quality: DataQuality
    metadata: QuantMetadata
```

## 2. 字段语义（防歧义，逐一明确）

| 字段 | 单位/含义 | 歧义风险点 → 本系统约定 |
|---|---|---|
| `as_of` | UTC datetime | 决策时点，不是数据生成时点 |
| `horizon` | 枚举 | 与 probability/expected_return 的期限绑定 |
| `expected_return` | 小数 | **标的收益**（不是策略收益）；策略收益在 TradeDecision 里 |
| `risk.max_loss` | 小数 | **账户净值比例**（-0.012 = -1.2% 账户净值），不是权利金/保证金口径 |
| `probability.*` | 0~1，和为 1 | **校准后**概率；raw 概率存 metadata，不对外 |
| `volatility` | 年化小数 | 与 horizon 对应 |
| `data_quality` | 见 §5 | 缺失/过期/异常必须标记 |

## 3. 各 State

```python
class InstrumentState(BaseModel):
    symbol: str                 # "SPY"
    price: float                # 收盘价
    prev_close: float
    day_return: float           # 当日收益
    dist_20ma: float            # 距 20MA 百分比
    dist_200ma: float

class TechnicalState(BaseModel):
    rsi_14: float
    atr_14: float
    realized_vol_20d: float     # 年化
    vwap: float | None
    volume_zscore: float | None

class MacroState(BaseModel):
    us5y: float                 # 收益率 %
    us5y_1d: float              # 1 日变化 bp
    us10y: float
    vix: float
    dxy: float
    wti: float
    wti_1d: float

class RegimeState(BaseModel):   # 多维，不是七选一
    trend: dict[str, float]     # {bull, bear, range} 和为 1
    volatility: dict[str, float]# {low, normal, high}
    macro: dict[str, float]     # {normal, shock}
    event: dict[str, float]     # {routine, event_driven}

class ProbabilityState(BaseModel):
    horizon: str
    up: float
    flat: float
    down: float
    calibrated: bool = True
    brier_score: float | None

class EventStudyState(BaseModel):
    condition: str              # 匹配条件描述
    n_samples: int              # 相似样本数
    evidence: str               # "sufficient" | "insufficient"
    p_down_close: float | None
    median_next_day: float | None
    median_2d: float | None

class OptionsState(BaseModel):  # 延后填充
    iv: float | None = None
    iv_rank: float | None = None
    gamma_wall: float | None = None
    zero_gamma: float | None = None
    gex: float | None = None

class RiskState(BaseModel):
    max_loss: float             # 账户净值比例
    expected_drawdown: float
    position_size: float | None # 建议仓位（Risk Engine 输出后填充）
```

## 4. 数据质量 + 版本

```python
class DataQuality(BaseModel):
    missing_fields: list[str]     # 缺失字段名
    stale_fields: list[str]       # 过期字段
    anomalies: list[str]          # 异常（如 WTI 负值）

class QuantMetadata(BaseModel):
    model_version: str            # "xgboost_v3"
    dataset_version: str          # "spy_pit_v7"
    feature_version: str          # "feature_set_2026_09_01"
    code_commit: str
    calibration_version: str | None
```

## 5. 完整示例

```json
{
  "schema_version": "1.0",
  "as_of": "2026-09-25T20:00:00Z",
  "horizon": "2d",
  "instrument": {"symbol": "SPY", "price": 771.35, "prev_close": 767.18,
                 "day_return": 0.0054, "dist_20ma": -0.011, "dist_200ma": 0.07},
  "technical": {"rsi_14": 41.2, "atr_14": 6.8, "realized_vol_20d": 0.18,
                "vwap": null, "volume_zscore": null},
  "macro": {"us5y": 5.01, "us5y_1d": -2, "us10y": 5.18, "vix": 14.87,
            "dxy": 100.97, "wti": 92.41, "wti_1d": -2.3},
  "regime": {"trend": {"bull": 0.62, "bear": 0.08, "range": 0.30},
             "volatility": {"low": 0.25, "normal": 0.65, "high": 0.10},
             "macro": {"normal": 0.85, "shock": 0.15},
             "event": {"routine": 0.90, "event_driven": 0.10}},
  "probability": {"horizon": "2d", "up": 0.58, "flat": 0.17, "down": 0.25,
                  "calibrated": true, "brier_score": 0.21},
  "event_study": {"condition": "vix<15 & sp<20ma", "n_samples": 143,
                  "evidence": "sufficient", "p_down_close": 0.36,
                  "median_next_day": -0.0012, "median_2d": 0.0031},
  "options": null,
  "risk": {"max_loss": -0.012, "expected_drawdown": -0.008, "position_size": null},
  "data_quality": {"missing_fields": ["vwap"], "stale_fields": [], "anomalies": []},
  "metadata": {"model_version": "xgb_v0", "dataset_version": "spy_pit_v1",
               "feature_version": "feat_v1", "code_commit": "TODO"}
}
```

## 6. 注入与渲染

`QuantState` 对象 → `QuantStateValidator`（校验：概率∈[0,1] 和为 1、max_loss 为负比例、as_of 不晚于今天、版本匹配）→ `Prompt Renderer` 按各 Agent 需求渲染成 Markdown 文本给 LLM。LLM 只见文本视图，结构化对象是唯一正式数据接口。
