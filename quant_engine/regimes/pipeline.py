# -*- coding: utf-8 -*-
"""Regime Pipeline：批量历史回放。"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from .engine import compute_regime


def run_regime_history(symbol: str = "SPY", start: str = "2024-01-01",
                       end: str = "2024-06-03", as_of: datetime | None = None) -> list:
    """对 [start, end] 每个交易日计算 RegimeState。"""
    from quant_engine.features.base import load_wide
    close = load_wide("daily", as_of=as_of)["close"]
    idx = [ts for ts in close.index if pd.Timestamp(start) <= ts <= pd.Timestamp(end)]
    return [compute_regime(symbol, ts, as_of) for ts in idx]
