# P4_REGIME_REGISTRY.md — Regime Registry

probability_type = RULE_BASED_REGIME_SCORE（归一化规则得分，非 ML 概率）

## 维度

| Dimension | States | 定义 | Version |
| --- | --- | --- | --- |
| trend | bull_trend, bear_trend, range | 价格相对 SMA20/50/200 的位置 + 均线排列 + 趋势斜率，判定趋势/震荡 | v1 |
| volatility | low_volatility, normal_volatility, high_volatility | VIX 水平 + realized vol + VIX 变化 + VIX 分位，判定低/正常/高波动 | v1 |
| macro | normal_macro, macro_shock | 美债/美元/原油单日异常变动，判定宏观是否处于 shock 状态 | v1 |
| event | normal_event, event_driven | 复用 P3 Event Engine，触发事件按 severity 加权，判定事件驱动程度 | v1 |

## 规则（27 条，versioned）

| Rule | Dimension | Condition | Weight | Version |
| --- | --- | --- | ---: | --- |
| price_above_sma20 | trend | `spy.distance_to_sma_20 > 0` | 1.0 | v1 |
| price_above_sma50 | trend | `spy.distance_to_sma_50 > 0` | 1.0 | v1 |
| price_above_sma200 | trend | `spy.distance_to_sma_200 > 0` | 1.0 | v1 |
| sma20_above_sma50 | trend | `spy.sma_20 > spy.sma_50` | 1.0 | v1 |
| sma50_above_sma200 | trend | `spy.sma_50 > spy.sma_200` | 1.0 | v1 |
| price_below_sma20 | trend | `spy.distance_to_sma_20 < 0` | 1.0 | v1 |
| price_below_sma50 | trend | `spy.distance_to_sma_50 < 0` | 1.0 | v1 |
| price_below_sma200 | trend | `spy.distance_to_sma_200 < 0` | 1.0 | v1 |
| sma20_below_sma50 | trend | `spy.sma_20 < spy.sma_50` | 1.0 | v1 |
| sma50_below_sma200 | trend | `spy.sma_50 < spy.sma_200` | 1.0 | v1 |
| price_near_sma20 | trend | `abs(spy.distance_to_sma_20) < 0.01` | 1.0 | v1 |
| sma20_sma50_proximity | trend | `abs(spy.sma_20 - spy.sma_50) / spy.sma_50 < 0.005` | 1.0 | v1 |
| low_trend_slope | trend | `abs(spy.close_slope_20) < 0.10` | 1.0 | v1 |
| vix_low | volatility | `vix_level < 15` | 1.0 | v1 |
| vix_normal | volatility | `15 <= vix_level <= 25` | 1.0 | v1 |
| vix_high | volatility | `vix_level > 25` | 1.0 | v1 |
| rv_low | volatility | `spy.realized_vol_20 < 0.10` | 1.0 | v1 |
| rv_normal | volatility | `0.10 <= spy.realized_vol_20 <= 0.20` | 1.0 | v1 |
| rv_high | volatility | `spy.realized_vol_20 > 0.20` | 1.0 | v1 |
| vix_shock_up | volatility | `macro.vix_change_1d > 0.10` | 1.0 | v1 |
| vix_percentile_high | volatility | `macro.vix_percentile_60 > 0.8` | 1.0 | v1 |
| vix_percentile_low | volatility | `macro.vix_percentile_60 < 0.2` | 1.0 | v1 |
| us10y_shock | macro | `abs(macro.us10y_change_1d) > 0.05` | 1.0 | v1 |
| us5y_shock | macro | `abs(macro.us5y_change_1d) > 0.05` | 1.0 | v1 |
| dxy_shock | macro | `abs(macro.dxy_change_1d) > 0.01` | 1.0 | v1 |
| wti_shock | macro | `abs(macro.wti_change_1d) > 0.05` | 1.0 | v1 |
| event_weighted_sum | event | `触发事件按 severity 权重累加` | 1.0 | v1 |
