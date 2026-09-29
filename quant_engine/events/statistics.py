# -*- coding: utf-8 -*-
"""Event Study 统计：event × horizon 的 N/mean/median/std/win_rate/percentiles。"""
from __future__ import annotations

import pandas as pd


def summarize(forward: list[dict]) -> pd.DataFrame:
    """输入 compute_forward_returns 的输出，返回 event × horizon 统计表。"""
    if not forward:
        return pd.DataFrame()
    df = pd.DataFrame(forward)
    rows = []
    for (event, horizon), g in df.groupby(["event_name", "horizon"]):
        r = g["forward_return"]
        rows.append({
            "event": event, "horizon": horizon, "N": len(r),
            "mean": r.mean(), "median": r.median(), "std": r.std(),
            "win_rate": (r > 0).mean(), "min": r.min(), "max": r.max(),
            "p25": r.quantile(0.25), "p75": r.quantile(0.75),
        })
    return pd.DataFrame(rows).sort_values(["event", "horizon"])
