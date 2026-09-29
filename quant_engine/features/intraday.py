# -*- coding: utf-8 -*-
"""Intraday Features：15m bar / session / 30m / 1h 聚合 + VWAP。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Feature


# ---------- 15m bar 级 ----------
class IntradayReturn(Feature):
    name = "spy_15m.return"
    definition = "15m bar close return"
    formula = "close_t / close_{t-1} - 1"
    input_fields = ["SPY.close"]
    frequency = "15m"
    lookback = 2
    unit = "ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].pct_change()


class IntradayLogReturn(Feature):
    name = "spy_15m.log_return"
    definition = "15m bar log return"
    formula = "ln(close_t / close_{t-1})"
    input_fields = ["SPY.close"]
    frequency = "15m"
    lookback = 2
    unit = "log ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return np.log(df["close"] / df["close"].shift(1))


class HighLowRange(Feature):
    name = "spy_15m.high_low_range"
    definition = "15m bar high-low range"
    formula = "high - low"
    input_fields = ["SPY.high", "SPY.low"]
    frequency = "15m"
    lookback = 1
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["high"] - df["low"]


class IntradayVolumeZScore(Feature):
    name = "spy_15m.volume_zscore"
    definition = "15m volume z-score over 20 bars (population std)"
    formula = "(volume - mean(volume,20)) / std(volume,20,ddof=0)"
    input_fields = ["SPY.volume"]
    frequency = "15m"
    lookback = 20
    unit = "z-score"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["volume"].rolling(20).mean()
        s = df["volume"].rolling(20).std(ddof=0)
        return (df["volume"] - m) / s


# ---------- session 级 ----------
def _session_series(df: pd.DataFrame, fn) -> pd.Series:
    """按 session（date）分组聚合，index = 每组最后一个 bar 的 timestamp。"""
    out, idx = [], []
    for _, g in df.groupby(df.index.date):
        out.append(fn(g))
        idx.append(g.index[-1])
    return pd.Series(out, index=pd.DatetimeIndex(idx))


class SessionReturn(Feature):
    name = "spy_session.return"
    definition = "session return (close_end / close_start - 1)"
    formula = "close[last] / close[first] - 1"
    input_fields = ["SPY.close"]
    frequency = "session"
    lookback = None
    unit = "ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return _session_series(df, lambda g: g["close"].iloc[-1] / g["close"].iloc[0] - 1)


class SessionHigh(Feature):
    name = "spy_session.high"
    definition = "session high"
    formula = "max(high in session)"
    input_fields = ["SPY.high"]
    frequency = "session"
    lookback = None
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return _session_series(df, lambda g: g["high"].max())


class SessionLow(Feature):
    name = "spy_session.low"
    definition = "session low"
    formula = "min(low in session)"
    input_fields = ["SPY.low"]
    frequency = "session"
    lookback = None
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return _session_series(df, lambda g: g["low"].min())


class DistanceFromSessionHigh(Feature):
    name = "spy_15m.distance_from_session_high"
    definition = "distance of bar close from session high"
    formula = "close / session_high - 1"
    input_fields = ["SPY.close", "SPY.high"]
    frequency = "15m"
    lookback = None
    unit = "ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sh = df["high"].groupby(df.index.date).transform("max")
        return df["close"] / sh - 1


class DistanceFromSessionLow(Feature):
    name = "spy_15m.distance_from_session_low"
    definition = "distance of bar close from session low"
    formula = "close / session_low - 1"
    input_fields = ["SPY.close", "SPY.low"]
    frequency = "15m"
    lookback = None
    unit = "ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        sl = df["low"].groupby(df.index.date).transform("min")
        return df["close"] / sl - 1


# ---------- VWAP（session 内累积，典型价格 (h+l+c)/3）----------
class VWAPSession(Feature):
    name = "spy_15m.vwap_session"
    definition = "session cumulative VWAP (typical price proxy)"
    formula = "VWAP_t = cumsum(tp*vol) / cumsum(vol), tp=(high+low+close)/3, per session"
    input_fields = ["SPY.high", "SPY.low", "SPY.close", "SPY.volume"]
    frequency = "15m"
    lookback = None
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        tp = (df["high"] + df["low"] + df["close"]) / 3
        num = (tp * df["volume"]).groupby(df.index.date).cumsum()
        den = df["volume"].groupby(df.index.date).cumsum()
        return num / den


# ---------- 30m / 1h 聚合（OHLC: open=first, high=max, low=min, close=last, vol=sum）----------
def resample_ohlcv(wide_15m: pd.DataFrame, freq: str) -> pd.DataFrame:
    """15m wide 表 → 30m/1h OHLCV。freq ∈ {'30min','1h'}。"""
    rule = {"30min": "30min", "1h": "1h"}[freq]
    agg = {}
    for col, how in [("open", "first"), ("high", "max"), ("low", "min"),
                     ("close", "last"), ("volume", "sum")]:
        if col in wide_15m.columns:
            agg[col] = how
    return wide_15m.resample(rule, label="right", closed="right").agg(agg).dropna(subset=["close"])
