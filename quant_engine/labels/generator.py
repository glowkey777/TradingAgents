# -*- coding: utf-8 -*-
"""Label Generator：future_return + dynamic threshold → UP/FLAT/DOWN。"""
from __future__ import annotations

from datetime import datetime
from math import sqrt

import pandas as pd

from quant_engine.features.base import load_wide
from quant_engine.features.pipeline import build_features

from .models import LabelDefinition, LabelRecord


def _realized_vol_series(symbol: str, start: str, end: str) -> pd.Series:
    pts = build_features(symbol, "daily", start=start, end=end,
                         feature_names=["spy.realized_vol_20"])
    s = pd.Series({pd.Timestamp(p.observation_time): p.value
                   for p in pts if p.quality_flag == "OK"})
    return s.sort_index()


def generate_labels(symbol: str, definition: LabelDefinition,
                    start: str = "2013-01-01", end: str = "2026-09-25",
                    source_data_version: str = "p1_v1") -> list[LabelRecord]:
    """生成 label。threshold = k × daily realized vol（PIT-safe）。"""
    close = load_wide("daily")["close"]
    rv = _realized_vol_series(symbol, start, end)
    n = int(definition.horizon.replace("T+", ""))

    idx = list(close.index)
    pos = {ts: i for i, ts in enumerate(idx)}
    records: list[LabelRecord] = []
    for i, ts in enumerate(idx):
        if ts < pd.Timestamp(start) or ts > pd.Timestamp(end):
            continue
        if i + n >= len(idx):
            continue  # 未来 endpoint 缺失 → 不生成 label（unavailable，非 FLAT）
        if ts not in rv.index:
            continue
        vol = rv.loc[ts]
        threshold = definition.threshold_multiplier * vol / sqrt(252)
        fwd = close.iloc[i + n] / close.iloc[i] - 1
        label = "UP" if fwd > threshold else ("DOWN" if fwd < -threshold else "FLAT")
        records.append(LabelRecord(
            symbol=symbol, observation_time=ts.to_pydatetime(),
            horizon=definition.horizon, future_return=float(fwd),
            threshold=float(threshold), label=label,
            label_version=definition.label_version,
            source_data_version=source_data_version,
            feature_cutoff="spy.realized_vol_20(T) 仅用 T 及以前",
        ))
    return records
