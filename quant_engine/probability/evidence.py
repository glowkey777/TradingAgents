# -*- coding: utf-8 -*-
"""Evidence Engine：构建历史状态表（regime 主导 + events + labels）。"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from quant_engine.features.pipeline import build_features
from quant_engine.features.base import load_macro_wide
from quant_engine.regimes import trend, volatility, macro
from quant_engine.regimes.inputs import FEATURE_NAMES
from quant_engine.events import detect_events
from quant_engine.labels import generate_labels, LABEL_DEFINITIONS


def _argmax(d: dict) -> str:
    return max(d, key=d.get) if d else "N/A"


def build_history_table(start: str, end: str, as_of: datetime | None = None) -> pd.DataFrame:
    """构建历史状态表（date index × 主导 regime + events + labels）。PIT-safe。"""
    pts = build_features("SPY", "daily", start=start, end=end,
                         as_of=as_of, feature_names=FEATURE_NAMES)
    rows = [p.model_dump() for p in pts if p.quality_flag == "OK"]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    wide = df.pivot_table(index="observation_time", columns="feature_name",
                          values="value", aggfunc="last")
    wide.index = pd.to_datetime(wide.index)
    wide = wide.sort_index()

    mdf = load_macro_wide(as_of=as_of)
    wide["vix_level"] = mdf["vix"].reindex(wide.index) if "vix" in mdf.columns else None

    recs = []
    for date, row in wide.iterrows():
        f = {c: (None if pd.isna(v) else float(v)) for c, v in row.items()}
        recs.append({
            "trend": _argmax(trend.score(f)),
            "volatility": _argmax(volatility.score(f)),
            "macro": _argmax(macro.score(f)),
        })
    table = pd.DataFrame(recs, index=wide.index)

    evs = detect_events("SPY", None, start, end, as_of)
    ev_map: dict = {}
    for e in evs:
        ev_map.setdefault(pd.Timestamp(e.observation_time).date(), set()).add(e.event_name)
    table["events"] = [ev_map.get(d.date(), set()) for d in table.index]

    l1 = {l.observation_time.date(): l.label
          for l in generate_labels("SPY", LABEL_DEFINITIONS["t1_up_flat_down"], start, end)}
    l2 = {l.observation_time.date(): l.label
          for l in generate_labels("SPY", LABEL_DEFINITIONS["t2_up_flat_down"], start, end)}
    table["label_t1"] = [l1.get(d.date()) for d in table.index]
    table["label_t2"] = [l2.get(d.date()) for d in table.index]
    return table
