# -*- coding: utf-8 -*-
"""Event Definitions：基于 P2 features 的显式事件（PIT 继承）。"""
from __future__ import annotations

import pandas as pd

from .base import Event


# ---------- Price Events ----------
class LargeUpDay(Event):
    name = "large_up_day"
    definition = "SPY 1D return exceeds +2%"
    input_features = ["spy.return_1d"]
    threshold = 0.02

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["spy.return_1d"] > 0.02


class LargeDownDay(Event):
    name = "large_down_day"
    definition = "SPY 1D return below -2%"
    input_features = ["spy.return_1d"]
    threshold = -0.02

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["spy.return_1d"] < -0.02


class LargeGapUp(Event):
    name = "large_gap_up"
    definition = "SPY opening gap exceeds +1.5%"
    input_features = ["spy.gap_1d"]
    threshold = 0.015

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["spy.gap_1d"] > 0.015


class LargeGapDown(Event):
    name = "large_gap_down"
    definition = "SPY opening gap below -1.5%"
    input_features = ["spy.gap_1d"]
    threshold = -0.015

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["spy.gap_1d"] < -0.015


# ---------- Volatility Events ----------
class VIXShockUp(Event):
    name = "vix_shock_up"
    definition = "VIX 1D change exceeds +10%"
    input_features = ["macro.vix_change_1d"]
    threshold = 0.10

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["macro.vix_change_1d"] > 0.10


class VIXShockDown(Event):
    name = "vix_shock_down"
    definition = "VIX 1D change below -10%"
    input_features = ["macro.vix_change_1d"]
    threshold = -0.10

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["macro.vix_change_1d"] < -0.10


class RealizedVolShock(Event):
    name = "realized_vol_shock"
    definition = "SPY 20-session realized vol exceeds 30% annualized"
    input_features = ["spy.realized_vol_20"]
    threshold = 0.30

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["spy.realized_vol_20"] > 0.30


# ---------- Trend Events ----------
def _make_above_sma(n: int) -> type[Event]:
    class _Above(Event):
        name = f"above_sma_{n}"
        definition = f"SPY close above {n}-session SMA"
        input_features = [f"spy.distance_to_sma_{n}"]
        threshold = 0.0

        def detect(self, df: pd.DataFrame) -> pd.Series:
            return df[f"spy.distance_to_sma_{n}"] > 0
    _Above.__name__ = f"AboveSMA{n}"
    return _Above


def _make_below_sma(n: int) -> type[Event]:
    class _Below(Event):
        name = f"below_sma_{n}"
        definition = f"SPY close below {n}-session SMA"
        input_features = [f"spy.distance_to_sma_{n}"]
        threshold = 0.0

        def detect(self, df: pd.DataFrame) -> pd.Series:
            return df[f"spy.distance_to_sma_{n}"] < 0
    _Below.__name__ = f"BelowSMA{n}"
    return _Below


AboveSMA20, AboveSMA50, AboveSMA200 = (_make_above_sma(n) for n in (20, 50, 200))
BelowSMA20, BelowSMA50, BelowSMA200 = (_make_below_sma(n) for n in (20, 50, 200))


class SMA20CrossSMA50(Event):
    name = "sma20_cross_sma50"
    definition = "SMA20 crosses above SMA50"
    input_features = ["spy.sma_20", "spy.sma_50"]
    threshold = None

    def detect(self, df: pd.DataFrame) -> pd.Series:
        diff = df["spy.sma_20"] - df["spy.sma_50"]
        return (diff > 0) & (diff.shift(1) <= 0)


class PriceCrossSMA20(Event):
    name = "price_cross_sma20"
    definition = "SPY close crosses above SMA20"
    input_features = ["spy.distance_to_sma_20"]
    threshold = None

    def detect(self, df: pd.DataFrame) -> pd.Series:
        d = df["spy.distance_to_sma_20"]
        return (d > 0) & (d.shift(1) <= 0)


class PriceCrossSMA50(Event):
    name = "price_cross_sma50"
    definition = "SPY close crosses above SMA50"
    input_features = ["spy.distance_to_sma_50"]
    threshold = None

    def detect(self, df: pd.DataFrame) -> pd.Series:
        d = df["spy.distance_to_sma_50"]
        return (d > 0) & (d.shift(1) <= 0)


# ---------- Momentum Events ----------
class RSIOverbought(Event):
    name = "rsi_overbought"
    definition = "SPY RSI14 exceeds 70"
    input_features = ["spy.rsi_14"]
    threshold = 70.0

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["spy.rsi_14"] > 70


class RSIOversold(Event):
    name = "rsi_oversold"
    definition = "SPY RSI14 below 30"
    input_features = ["spy.rsi_14"]
    threshold = 30.0

    def detect(self, df: pd.DataFrame) -> pd.Series:
        return df["spy.rsi_14"] < 30


class MACDBullishCross(Event):
    name = "macd_bullish_cross"
    definition = "MACD line crosses above signal"
    input_features = ["spy.macd_line", "spy.macd_signal"]
    threshold = None

    def detect(self, df: pd.DataFrame) -> pd.Series:
        diff = df["spy.macd_line"] - df["spy.macd_signal"]
        return (diff > 0) & (diff.shift(1) <= 0)


class MACDBearishCross(Event):
    name = "macd_bearish_cross"
    definition = "MACD line crosses below signal"
    input_features = ["spy.macd_line", "spy.macd_signal"]
    threshold = None

    def detect(self, df: pd.DataFrame) -> pd.Series:
        diff = df["spy.macd_line"] - df["spy.macd_signal"]
        return (diff < 0) & (diff.shift(1) >= 0)


# ---------- Macro Shock Events ----------
def _make_macro_shock(field: str, th: float) -> type[Event]:
    class _Shock(Event):
        name = f"{field}_shock"
        definition = f"{field.upper()} 1D absolute change exceeds {th:.0%}"
        input_features = [f"macro.{field}_change_1d"]
        threshold = th

        def detect(self, df: pd.DataFrame) -> pd.Series:
            return df[f"macro.{field}_change_1d"].abs() > th
    _Shock.__name__ = f"{field.upper()}Shock"
    return _Shock


US10YShock = _make_macro_shock("us10y", 0.05)
US5YShock = _make_macro_shock("us5y", 0.05)
DXYShock = _make_macro_shock("dxy", 0.01)
WTIShock = _make_macro_shock("wti", 0.05)
