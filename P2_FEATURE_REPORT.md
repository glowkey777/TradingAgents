# P2_FEATURE_REPORT.md — P2 Feature Engine 报告

## Coverage & Missing

| 频率 | 总点数 | OK | INSUFFICIENT_HISTORY |
| --- | ---: | ---: | ---: |
| daily | 7208 | 5096 | 2112 |
| 15m | 182 | 161 | 21 |
| session | 3 | 3 | 0 |

## Feature Coverage（daily 全量）

| feature | first | last | OK rows |
| --- | ---: | ---: | ---: |
| macro.dxy_change_1d | 2013-01-03 | 2026-09-25 | 3449 |
| macro.dxy_change_20d | 2013-01-31 | 2026-09-25 | 3430 |
| macro.dxy_change_5d | 2013-01-09 | 2026-09-25 | 3445 |
| macro.dxy_percentile_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.dxy_percentile_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.dxy_zscore_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.dxy_zscore_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.us10y_change_1d | 2013-01-03 | 2026-09-25 | 3449 |
| macro.us10y_change_20d | 2013-01-31 | 2026-09-25 | 3430 |
| macro.us10y_change_5d | 2013-01-09 | 2026-09-25 | 3445 |
| macro.us10y_percentile_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.us10y_percentile_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.us10y_us5y_spread | 2013-01-02 | 2026-09-25 | 3452 |
| macro.us10y_us5y_spread_change_1d | 2013-01-03 | 2026-09-25 | 3449 |
| macro.us10y_us5y_spread_zscore_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.us10y_zscore_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.us10y_zscore_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.us5y_change_1d | 2013-01-03 | 2026-09-25 | 3449 |
| macro.us5y_change_20d | 2013-01-31 | 2026-09-25 | 3430 |
| macro.us5y_change_5d | 2013-01-09 | 2026-09-25 | 3445 |
| macro.us5y_percentile_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.us5y_percentile_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.us5y_zscore_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.us5y_zscore_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.vix_change_1d | 2013-01-03 | 2026-09-25 | 3449 |
| macro.vix_change_20d | 2013-01-31 | 2026-09-25 | 3430 |
| macro.vix_change_5d | 2013-01-09 | 2026-09-25 | 3445 |
| macro.vix_percentile_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.vix_percentile_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.vix_zscore_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.vix_zscore_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.wti_change_1d | 2013-01-03 | 2026-09-25 | 3449 |
| macro.wti_change_20d | 2013-01-31 | 2026-09-25 | 3430 |
| macro.wti_change_5d | 2013-01-09 | 2026-09-25 | 3445 |
| macro.wti_percentile_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.wti_percentile_60 | 2013-03-28 | 2026-09-25 | 3311 |
| macro.wti_zscore_20 | 2013-01-30 | 2026-09-25 | 3395 |
| macro.wti_zscore_60 | 2013-03-28 | 2026-09-25 | 3311 |
| spy.adx_14 | 2013-03-01 | 2026-09-25 | 3414 |
| spy.atr_14 | 2013-01-22 | 2026-09-25 | 3441 |
| spy.bb_lower | 2013-01-30 | 2026-09-25 | 3435 |
| spy.bb_middle | 2013-01-30 | 2026-09-25 | 3435 |
| spy.bb_position | 2013-01-30 | 2026-09-25 | 3435 |
| spy.bb_upper | 2013-01-30 | 2026-09-25 | 3435 |
| spy.bb_width | 2013-01-30 | 2026-09-25 | 3435 |
| spy.close_slope_20 | 2013-01-30 | 2026-09-25 | 3435 |
| spy.close_slope_50 | 2013-03-14 | 2026-09-25 | 3405 |
| spy.distance_to_sma_100 | 2013-05-24 | 2026-09-25 | 3355 |
| spy.distance_to_sma_20 | 2013-01-30 | 2026-09-25 | 3435 |
| spy.distance_to_sma_200 | 2013-10-16 | 2026-09-25 | 3255 |
| spy.distance_to_sma_50 | 2013-03-14 | 2026-09-25 | 3405 |
| spy.ema_100 | 2013-05-24 | 2026-09-25 | 3355 |
| spy.ema_20 | 2013-01-30 | 2026-09-25 | 3435 |
| spy.ema_200 | 2013-10-16 | 2026-09-25 | 3255 |
| spy.ema_50 | 2013-03-14 | 2026-09-25 | 3405 |
| spy.gap_1d | 2013-01-03 | 2026-09-25 | 3453 |
| spy.log_return_1d | 2013-01-03 | 2026-09-25 | 3453 |
| spy.macd_histogram | 2013-02-20 | 2026-09-25 | 3421 |
| spy.macd_line | 2013-02-07 | 2026-09-25 | 3429 |
| spy.macd_signal | 2013-02-20 | 2026-09-25 | 3421 |
| spy.realized_vol_20 | 2013-01-31 | 2026-09-25 | 3434 |
| spy.return_1d | 2013-01-03 | 2026-09-25 | 3453 |
| spy.rsi_14 | 2013-01-23 | 2026-09-25 | 3440 |
| spy.sma_100 | 2013-05-24 | 2026-09-25 | 3355 |
| spy.sma_20 | 2013-01-30 | 2026-09-25 | 3435 |
| spy.sma_200 | 2013-10-16 | 2026-09-25 | 3255 |
| spy.sma_50 | 2013-03-14 | 2026-09-25 | 3405 |
| spy.volume_zscore_20 | 2013-01-30 | 2026-09-25 | 3435 |

## 验收汇总

| 项 | 结果 |
| --- | --- |
| Reproducibility (determinism) | ✅ 同输入同输出 |
| PIT leakage (lookahead) | ✅ 0 违例 |
| Golden Feature Regression | ✅ 12/12 |
| Independent verification | ✅ SMA/EMA/RSI/ATR/MACD/BB/RV 手算一致 |
| P1 immutability | ✅ 只读 load_wide，无 write |
| Feature versioning | ✅ 每 feature 有 feature_version |
| 总 feature 数 | ✅ 78 |
