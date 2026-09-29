# -*- coding: utf-8 -*-
"""Regime Input：从 P2 features + P3 events 收集某时点的输入（PIT-safe）。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from quant_engine.features.pipeline import build_features
from quant_engine.features.base import load_macro_wide

FEATURE_NAMES = [
    "spy.distance_to_sma_20", "spy.distance_to_sma_50", "spy.distance_to_sma_200",
    "spy.sma_20", "spy.sma_50", "spy.sma_200", "spy.close_slope_20",
    "spy.realized_vol_20", "spy.atr_14",
    "macro.vix_change_1d", "macro.vix_percentile_60",
    "macro.us10y_change_1d", "macro.us5y_change_1d",
    "macro.dxy_change_1d", "macro.wti_change_1d",
    "macro.us10y_us5y_spread",
]

WARMUP_DAYS = 320  # 覆盖 sma_200（200 交易日 ≈ 280 日历天）+ vix_percentile_60 + MACD 收敛


def collect_features(symbol: str, observation_time, as_of: datetime | None) -> dict[str, float | None]:
    ts = pd.Timestamp(observation_time)
    day = ts.normalize()
    start = str((day - timedelta(days=WARMUP_DAYS)).date())
    end = str(day.date())
    pts = build_features(symbol, "daily", start=start, end=end,
                         as_of=as_of, feature_names=FEATURE_NAMES)
    out: dict[str, float | None] = {name: None for name in FEATURE_NAMES}
    for p in pts:
        if p.observation_time.date() == day.date() and p.quality_flag == "OK":
            out[p.feature_name] = p.value
    # vix level（原始值，来自 macro CSV，非 P2 feature）
    mdf = load_macro_wide(as_of=as_of)
    out["vix_level"] = None
    if ts in mdf.index and "vix" in mdf.columns:
        v = mdf.loc[ts, "vix"]
        out["vix_level"] = float(v) if not pd.isna(v) else None
    return out
