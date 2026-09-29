# P2_FEATURE_REGISTRY.md — Feature Registry

共 78 个 feature。看表即知怎么算。

| Feature | Formula | Input | Lookback | Frequency | PIT | Version |
| ------- | ------- | ----- | -------: | --------- | --- | ------- |
| spy.return_1d | close_t / close_{t-1} - 1 | SPY.close | 2 | daily | YES | v1 |
| spy.log_return_1d | ln(close_t / close_{t-1}) | SPY.close | 2 | daily | YES | v1 |
| spy.sma_20 | mean(close[t-20+1 : t]) | SPY.close | 20 | daily | YES | v1 |
| spy.sma_50 | mean(close[t-50+1 : t]) | SPY.close | 50 | daily | YES | v1 |
| spy.sma_100 | mean(close[t-100+1 : t]) | SPY.close | 100 | daily | YES | v1 |
| spy.sma_200 | mean(close[t-200+1 : t]) | SPY.close | 200 | daily | YES | v1 |
| spy.ema_20 | EMA_t = alpha*close_t + (1-alpha)*EMA_{t-1}, alpha=2/(20+1), adjust=False, min_periods=20 | SPY.close | 20 | daily | YES | v1 |
| spy.ema_50 | EMA_t = alpha*close_t + (1-alpha)*EMA_{t-1}, alpha=2/(50+1), adjust=False, min_periods=50 | SPY.close | 50 | daily | YES | v1 |
| spy.ema_100 | EMA_t = alpha*close_t + (1-alpha)*EMA_{t-1}, alpha=2/(100+1), adjust=False, min_periods=100 | SPY.close | 100 | daily | YES | v1 |
| spy.ema_200 | EMA_t = alpha*close_t + (1-alpha)*EMA_{t-1}, alpha=2/(200+1), adjust=False, min_periods=200 | SPY.close | 200 | daily | YES | v1 |
| spy.distance_to_sma_20 | close / SMA_20 - 1 | SPY.close | 20 | daily | YES | v1 |
| spy.distance_to_sma_50 | close / SMA_50 - 1 | SPY.close | 50 | daily | YES | v1 |
| spy.distance_to_sma_100 | close / SMA_100 - 1 | SPY.close | 100 | daily | YES | v1 |
| spy.distance_to_sma_200 | close / SMA_200 - 1 | SPY.close | 200 | daily | YES | v1 |
| spy.atr_14 | TR_t = max(high-low, |high-prev_close|, |low-prev_close|); ATR = Wilder EWM(TR, alpha=1/14, min_periods=14) | SPY.high,SPY.low,SPY.close | 14 | daily | YES | v1 |
| spy.rsi_14 | delta=close.diff(); gain=clip(delta,0); loss=clip(-delta,0); avg_gain/avg_loss = Wilder EWM(alpha=1/14); RSI = 100 - 100/(1+RS) | SPY.close | 14 | daily | YES | v1 |
| spy.macd_line | EMA12 - EMA26 (adjust=False) | SPY.close | 26 | daily | YES | v1 |
| spy.macd_signal | EMA9(MACD line) | SPY.close | 35 | daily | YES | v1 |
| spy.macd_histogram | MACD line - signal line | SPY.close | 35 | daily | YES | v1 |
| spy.adx_14 | +DM/-DM Wilder-smoothed; +DI=100*+DM/TR; -DI=100*-DM/TR; DX=100*|+DI--DI|/(+DI+-DI); ADX=Wilder EWM(DX) | SPY.high,SPY.low,SPY.close | 28 | daily | YES | v1 |
| spy.bb_middle | mean(close, 20) | SPY.close | 20 | daily | YES | v1 |
| spy.bb_upper | middle + 2*std(close,20,ddof=0) | SPY.close | 20 | daily | YES | v1 |
| spy.bb_lower | middle - 2*std(close,20,ddof=0) | SPY.close | 20 | daily | YES | v1 |
| spy.bb_width | (upper - lower) / middle | SPY.close | 20 | daily | YES | v1 |
| spy.bb_position | (close - lower) / (upper - lower) | SPY.close | 20 | daily | YES | v1 |
| spy.realized_vol_20 | sqrt(252) * std(log_return, 20, ddof=0) | SPY.close | 21 | daily | YES | v1 |
| spy.gap_1d | open_t / close_{t-1} - 1 | SPY.open,SPY.close | 2 | daily | YES | v1 |
| spy.volume_zscore_20 | (volume - mean(volume,20)) / std(volume,20,ddof=0) | SPY.volume | 20 | daily | YES | v1 |
| spy.close_slope_20 | slope = cov(x, close[t-20+1:t]) / var(x), x = 0..20-1 | SPY.close | 20 | daily | YES | v1 |
| spy.close_slope_50 | slope = cov(x, close[t-50+1:t]) / var(x), x = 0..50-1 | SPY.close | 50 | daily | YES | v1 |
| spy_15m.return | close_t / close_{t-1} - 1 | SPY.close | 2 | 15m | YES | v1 |
| spy_15m.log_return | ln(close_t / close_{t-1}) | SPY.close | 2 | 15m | YES | v1 |
| spy_15m.high_low_range | high - low | SPY.high,SPY.low | 1 | 15m | YES | v1 |
| spy_15m.volume_zscore | (volume - mean(volume,20)) / std(volume,20,ddof=0) | SPY.volume | 20 | 15m | YES | v1 |
| spy_session.return | close[last] / close[first] - 1 | SPY.close | - | session | YES | v1 |
| spy_session.high | max(high in session) | SPY.high | - | session | YES | v1 |
| spy_session.low | min(low in session) | SPY.low | - | session | YES | v1 |
| spy_15m.distance_from_session_high | close / session_high - 1 | SPY.close,SPY.high | - | 15m | YES | v1 |
| spy_15m.distance_from_session_low | close / session_low - 1 | SPY.close,SPY.low | - | 15m | YES | v1 |
| spy_15m.vwap_session | VWAP_t = cumsum(tp*vol) / cumsum(vol), tp=(high+low+close)/3, per session | SPY.high,SPY.low,SPY.close,SPY.volume | - | 15m | YES | v1 |
| macro.us10y_us5y_spread | us10y - us5y | US10Y,US5Y | 1 | daily | YES | v1 |
| macro.us10y_us5y_spread_change_1d | spread_t - spread_{t-1} | US10Y,US5Y | 2 | daily | YES | v1 |
| macro.us10y_us5y_spread_zscore_20 | (spread - mean(spread,20)) / std(spread,20,ddof=0) | US10Y,US5Y | 20 | daily | YES | v1 |
| macro.vix_change_1d | vix_t / vix_{t-1} - 1 | VIX | 2 | daily | YES | v1 |
| macro.vix_change_5d | vix_t / vix_{t-5} - 1 | VIX | 6 | daily | YES | v1 |
| macro.vix_change_20d | vix_t / vix_{t-20} - 1 | VIX | 21 | daily | YES | v1 |
| macro.vix_zscore_20 | (vix - mean(vix,20)) / std(vix,20,ddof=0) | VIX | 20 | daily | YES | v1 |
| macro.vix_percentile_20 | rank of current value within trailing 20 observations | VIX | 20 | daily | YES | v1 |
| macro.vix_zscore_60 | (vix - mean(vix,60)) / std(vix,60,ddof=0) | VIX | 60 | daily | YES | v1 |
| macro.vix_percentile_60 | rank of current value within trailing 60 observations | VIX | 60 | daily | YES | v1 |
| macro.us5y_change_1d | us5y_t / us5y_{t-1} - 1 | US5Y | 2 | daily | YES | v1 |
| macro.us5y_change_5d | us5y_t / us5y_{t-5} - 1 | US5Y | 6 | daily | YES | v1 |
| macro.us5y_change_20d | us5y_t / us5y_{t-20} - 1 | US5Y | 21 | daily | YES | v1 |
| macro.us5y_zscore_20 | (us5y - mean(us5y,20)) / std(us5y,20,ddof=0) | US5Y | 20 | daily | YES | v1 |
| macro.us5y_percentile_20 | rank of current value within trailing 20 observations | US5Y | 20 | daily | YES | v1 |
| macro.us5y_zscore_60 | (us5y - mean(us5y,60)) / std(us5y,60,ddof=0) | US5Y | 60 | daily | YES | v1 |
| macro.us5y_percentile_60 | rank of current value within trailing 60 observations | US5Y | 60 | daily | YES | v1 |
| macro.us10y_change_1d | us10y_t / us10y_{t-1} - 1 | US10Y | 2 | daily | YES | v1 |
| macro.us10y_change_5d | us10y_t / us10y_{t-5} - 1 | US10Y | 6 | daily | YES | v1 |
| macro.us10y_change_20d | us10y_t / us10y_{t-20} - 1 | US10Y | 21 | daily | YES | v1 |
| macro.us10y_zscore_20 | (us10y - mean(us10y,20)) / std(us10y,20,ddof=0) | US10Y | 20 | daily | YES | v1 |
| macro.us10y_percentile_20 | rank of current value within trailing 20 observations | US10Y | 20 | daily | YES | v1 |
| macro.us10y_zscore_60 | (us10y - mean(us10y,60)) / std(us10y,60,ddof=0) | US10Y | 60 | daily | YES | v1 |
| macro.us10y_percentile_60 | rank of current value within trailing 60 observations | US10Y | 60 | daily | YES | v1 |
| macro.dxy_change_1d | dxy_t / dxy_{t-1} - 1 | DXY | 2 | daily | YES | v1 |
| macro.dxy_change_5d | dxy_t / dxy_{t-5} - 1 | DXY | 6 | daily | YES | v1 |
| macro.dxy_change_20d | dxy_t / dxy_{t-20} - 1 | DXY | 21 | daily | YES | v1 |
| macro.dxy_zscore_20 | (dxy - mean(dxy,20)) / std(dxy,20,ddof=0) | DXY | 20 | daily | YES | v1 |
| macro.dxy_percentile_20 | rank of current value within trailing 20 observations | DXY | 20 | daily | YES | v1 |
| macro.dxy_zscore_60 | (dxy - mean(dxy,60)) / std(dxy,60,ddof=0) | DXY | 60 | daily | YES | v1 |
| macro.dxy_percentile_60 | rank of current value within trailing 60 observations | DXY | 60 | daily | YES | v1 |
| macro.wti_change_1d | wti_t / wti_{t-1} - 1 | WTI | 2 | daily | YES | v1 |
| macro.wti_change_5d | wti_t / wti_{t-5} - 1 | WTI | 6 | daily | YES | v1 |
| macro.wti_change_20d | wti_t / wti_{t-20} - 1 | WTI | 21 | daily | YES | v1 |
| macro.wti_zscore_20 | (wti - mean(wti,20)) / std(wti,20,ddof=0) | WTI | 20 | daily | YES | v1 |
| macro.wti_percentile_20 | rank of current value within trailing 20 observations | WTI | 20 | daily | YES | v1 |
| macro.wti_zscore_60 | (wti - mean(wti,60)) / std(wti,60,ddof=0) | WTI | 60 | daily | YES | v1 |
| macro.wti_percentile_60 | rank of current value within trailing 60 observations | WTI | 60 | daily | YES | v1 |
