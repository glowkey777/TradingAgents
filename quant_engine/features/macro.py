# -*- coding: utf-8 -*-
"""Macro Features：Change / Z-score / Percentile / Yield spread（PIT-safe rolling）。"""
from __future__ import annotations

import pandas as pd

from .base import Feature, load_macro_wide


def _macro_series(field: str) -> pd.Series:
    return load_macro_wide()[field]


# ---------- Change ----------
def _make_change(field: str, n: int) -> type[Feature]:
    col = {"vix": "vix", "us5y": "us5y", "us10y": "us10y", "dxy": "dxy", "wti": "wti"}[field]

    class _Chg(Feature):
        name = f"macro.{field}_change_{n}d"
        definition = f"{n}-session change of {field.upper()}"
        formula = f"{col}_t / {col}_{{t-{n}}} - 1"
        input_fields = [f"{field.upper()}"]
        frequency = "daily"
        lookback = n + 1
        unit = "ratio"

        def compute(self, df: pd.DataFrame) -> pd.Series:
            s = load_macro_wide().reindex(df.index)[col]
            return s / s.shift(n) - 1
    _Chg.__name__ = f"{field.upper()}Chg{n}"
    return _Chg


# ---------- Z-score ----------
def _make_zscore(field: str, n: int) -> type[Feature]:
    col = {"vix": "vix", "us5y": "us5y", "us10y": "us10y", "dxy": "dxy", "wti": "wti"}[field]

    class _Z(Feature):
        name = f"macro.{field}_zscore_{n}"
        definition = f"{n}-session rolling z-score of {field.upper()} (population std)"
        formula = f"({col} - mean({col},{n})) / std({col},{n},ddof=0)"
        input_fields = [f"{field.upper()}"]
        frequency = "daily"
        lookback = n
        unit = "z-score"

        def compute(self, df: pd.DataFrame) -> pd.Series:
            s = load_macro_wide().reindex(df.index)[col]
            return (s - s.rolling(n).mean()) / s.rolling(n).std(ddof=0)
    _Z.__name__ = f"{field.upper()}Z{n}"
    return _Z


# ---------- Rolling Percentile（PIT-safe，只用当时及之前）----------
def _make_percentile(field: str, n: int) -> type[Feature]:
    col = {"vix": "vix", "us5y": "us5y", "us10y": "us10y", "dxy": "dxy", "wti": "wti"}[field]

    class _P(Feature):
        name = f"macro.{field}_percentile_{n}"
        definition = f"{n}-session rolling percentile rank of {field.upper()}"
        formula = f"rank of current value within trailing {n} observations"
        input_fields = [f"{field.upper()}"]
        frequency = "daily"
        lookback = n
        unit = "percentile (0-1)"

        def compute(self, df: pd.DataFrame) -> pd.Series:
            s = load_macro_wide().reindex(df.index)[col]
            return s.rolling(n).apply(lambda x: (x[-1] >= x[:-1]).mean(), raw=True)
    _P.__name__ = f"{field.upper()}Pct{n}"
    return _P


# ---------- Yield spread (10Y-5Y) ----------
class YieldSpreadLevel(Feature):
    name = "macro.us10y_us5y_spread"
    definition = "US10Y - US5Y yield spread level"
    formula = "us10y - us5y"
    input_fields = ["US10Y", "US5Y"]
    frequency = "daily"
    lookback = 1
    unit = "percent"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = load_macro_wide().reindex(df.index)
        return m["us10y"] - m["us5y"]


class YieldSpreadChange1D(Feature):
    name = "macro.us10y_us5y_spread_change_1d"
    definition = "1-session change of 10Y-5Y spread"
    formula = "spread_t - spread_{t-1}"
    input_fields = ["US10Y", "US5Y"]
    frequency = "daily"
    lookback = 2
    unit = "percent"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = load_macro_wide().reindex(df.index)
        return (m["us10y"] - m["us5y"]).diff()


class YieldSpreadZScore20(Feature):
    name = "macro.us10y_us5y_spread_zscore_20"
    definition = "20-session rolling z-score of 10Y-5Y spread"
    formula = "(spread - mean(spread,20)) / std(spread,20,ddof=0)"
    input_fields = ["US10Y", "US5Y"]
    frequency = "daily"
    lookback = 20
    unit = "z-score"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = load_macro_wide().reindex(df.index)
        s = m["us10y"] - m["us5y"]
        return (s - s.rolling(20).mean()) / s.rolling(20).std(ddof=0)


# 实例化：VIX/US5Y/US10Y/DXY/WTI 各 1D/5D/20D change + 20/60 zscore + 20/60 percentile
for _f in ("vix", "us5y", "us10y", "dxy", "wti"):
    for _n in (1, 5, 20):
        _make_change(_f, _n)
    for _n in (20, 60):
        _make_zscore(_f, _n)
        _make_percentile(_f, _n)
