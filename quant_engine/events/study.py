# -*- coding: utf-8 -*-
"""Event Study：事件 → forward return。"""
from __future__ import annotations

import pandas as pd

from quant_engine.features.base import load_wide

from .models import EventRecord

HORIZONS = ["T+1", "T+2", "T+5"]


def compute_forward_returns(events: list[EventRecord], horizons: list[str] | None = None,
                            as_of: datetime = None) -> list[dict]:
    """对每个事件计算 forward return（用交易日索引，PIT-safe）。"""
    horizons = horizons or HORIZONS
    close = load_wide("daily", as_of=as_of)["close"]
    idx = list(close.index)
    pos = {ts: i for i, ts in enumerate(idx)}

    out = []
    for ev in events:
        ts = pd.Timestamp(ev.observation_time)
        if ts not in pos:
            continue
        i = pos[ts]
        for h in horizons:
            n = int(h.replace("T+", ""))
            if i + n >= len(idx):
                continue
            fwd = close.iloc[i + n] / close.iloc[i] - 1
            out.append({
                "event_name": ev.event_name, "observation_time": ts,
                "horizon": h, "forward_return": float(fwd),
            })
    return out
