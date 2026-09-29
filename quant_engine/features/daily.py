# -*- coding: utf-8 -*-
"""Daily Technical Features（无 look-ahead，公式锁定，PIT 继承）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Feature


# ---------- Return ----------
class Return1D(Feature):
    name = "spy.return_1d"
    definition = "1-session close return"
    formula = "close_t / close_{t-1} - 1"
    input_fields = ["SPY.close"]
    lookback = 2
    unit = "ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].pct_change()


class LogReturn1D(Feature):
    name = "spy.log_return_1d"
    definition = "1-session log return"
    formula = "ln(close_t / close_{t-1})"
    input_fields = ["SPY.close"]
    lookback = 2
    unit = "log ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return np.log(df["close"] / df["close"].shift(1))


# ---------- SMA / EMA / Distance ----------
def _make_sma(n: int) -> type[Feature]:
    class _SMA(Feature):
        name = f"spy.sma_{n}"
        definition = f"{n}-session simple moving average of close"
        formula = f"mean(close[t-{n}+1 : t])"
        input_fields = ["SPY.close"]
        lookback = n
        unit = "price"

        def compute(self, df: pd.DataFrame) -> pd.Series:
            return df["close"].rolling(n).mean()
    _SMA.__name__ = f"SMA{n}"
    return _SMA


def _make_ema(n: int) -> type[Feature]:
    class _EMA(Feature):
        name = f"spy.ema_{n}"
        definition = f"{n}-session exponential moving average of close"
        formula = f"EMA_t = alpha*close_t + (1-alpha)*EMA_{{t-1}}, alpha=2/({n}+1), adjust=False, min_periods={n}"
        input_fields = ["SPY.close"]
        lookback = n
        unit = "price"

        def compute(self, df: pd.DataFrame) -> pd.Series:
            return df["close"].ewm(span=n, adjust=False, min_periods=n).mean()
    _EMA.__name__ = f"EMA{n}"
    return _EMA


def _make_dist_sma(n: int) -> type[Feature]:
    class _Dist(Feature):
        name = f"spy.distance_to_sma_{n}"
        definition = f"distance of close to {n}-session SMA"
        formula = f"close / SMA_{n} - 1"
        input_fields = ["SPY.close"]
        lookback = n
        unit = "ratio"

        def compute(self, df: pd.DataFrame) -> pd.Series:
            return df["close"] / df["close"].rolling(n).mean() - 1
    _Dist.__name__ = f"DistSMA{n}"
    return _Dist


SMA20, SMA50, SMA100, SMA200 = (_make_sma(n) for n in (20, 50, 100, 200))
EMA20, EMA50, EMA100, EMA200 = (_make_ema(n) for n in (20, 50, 100, 200))
DistSMA20, DistSMA50, DistSMA100, DistSMA200 = (_make_dist_sma(n) for n in (20, 50, 100, 200))


# ---------- ATR (Wilder) ----------
class ATR14(Feature):
    name = "spy.atr_14"
    definition = "14-session Average True Range (Wilder smoothing)"
    formula = ("TR_t = max(high-low, |high-prev_close|, |low-prev_close|); "
               "ATR = Wilder EWM(TR, alpha=1/14, min_periods=14)")
    input_fields = ["SPY.high", "SPY.low", "SPY.close"]
    lookback = 14
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        prev_close = df["close"].shift(1)
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()


# ---------- RSI (Wilder) ----------
class RSI14(Feature):
    name = "spy.rsi_14"
    definition = "14-session Relative Strength Index (Wilder smoothing)"
    formula = ("delta=close.diff(); gain=clip(delta,0); loss=clip(-delta,0); "
               "avg_gain/avg_loss = Wilder EWM(alpha=1/14); RSI = 100 - 100/(1+RS)")
    input_fields = ["SPY.close"]
    lookback = 14
    unit = "index (0-100)"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)


# ---------- MACD ----------
class _MACDBase:
    input_fields = ["SPY.close"]

    @staticmethod
    def _macd(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
        ema12 = df["close"].ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = df["close"].ewm(span=26, adjust=False, min_periods=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False, min_periods=9).mean()
        return macd, signal, macd - signal


class MACDLine(Feature, _MACDBase):
    name = "spy.macd_line"
    definition = "MACD line (EMA12 - EMA26)"
    formula = "EMA12 - EMA26 (adjust=False)"
    input_fields = ["SPY.close"]
    lookback = 26
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return self._macd(df)[0]


class MACDSignal(Feature, _MACDBase):
    name = "spy.macd_signal"
    definition = "MACD signal line (9-session EMA of MACD)"
    formula = "EMA9(MACD line)"
    input_fields = ["SPY.close"]
    lookback = 35
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return self._macd(df)[1]


class MACDHistogram(Feature, _MACDBase):
    name = "spy.macd_histogram"
    definition = "MACD histogram (MACD line - signal)"
    formula = "MACD line - signal line"
    input_fields = ["SPY.close"]
    lookback = 35
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return self._macd(df)[2]


# ---------- ADX (Wilder) ----------
class ADX14(Feature):
    name = "spy.adx_14"
    definition = "14-session Average Directional Index (Wilder)"
    formula = ("+DM/-DM Wilder-smoothed; +DI=100*+DM/TR; -DI=100*-DM/TR; "
               "DX=100*|+DI--DI|/(+DI+-DI); ADX=Wilder EWM(DX)")
    input_fields = ["SPY.high", "SPY.low", "SPY.close"]
    lookback = 28
    unit = "index (0-100)"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        up = df["high"].diff()
        down = -df["low"].diff()
        plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
        minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
        prev_close = df["close"].shift(1)
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        return dx.ewm(alpha=1 / 14, adjust=False, min_periods=28).mean()


# ---------- Bollinger (population std, period=20, mult=2) ----------
class BB(Feature):
    name = "spy.bb_middle"
    definition = "Bollinger middle band (20-session SMA)"
    formula = "mean(close, 20)"
    input_fields = ["SPY.close"]
    lookback = 20
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(20).mean()


class BBUpper(Feature):
    name = "spy.bb_upper"
    definition = "Bollinger upper band (population std, mult=2)"
    formula = "middle + 2*std(close,20,ddof=0)"
    input_fields = ["SPY.close"]
    lookback = 20
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["close"].rolling(20).mean()
        s = df["close"].rolling(20).std(ddof=0)
        return m + 2 * s


class BBLower(Feature):
    name = "spy.bb_lower"
    definition = "Bollinger lower band (population std, mult=2)"
    formula = "middle - 2*std(close,20,ddof=0)"
    input_fields = ["SPY.close"]
    lookback = 20
    unit = "price"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["close"].rolling(20).mean()
        s = df["close"].rolling(20).std(ddof=0)
        return m - 2 * s


class BBWidth(Feature):
    name = "spy.bb_width"
    definition = "Bollinger band width (normalized)"
    formula = "(upper - lower) / middle"
    input_fields = ["SPY.close"]
    lookback = 20
    unit = "ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["close"].rolling(20).mean()
        s = df["close"].rolling(20).std(ddof=0)
        return 4 * s / m


class BBPosition(Feature):
    name = "spy.bb_position"
    definition = "Bollinger %B position of close within bands"
    formula = "(close - lower) / (upper - lower)"
    input_fields = ["SPY.close"]
    lookback = 20
    unit = "ratio (0-1)"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["close"].rolling(20).mean()
        s = df["close"].rolling(20).std(ddof=0)
        upper, lower = m + 2 * s, m - 2 * s
        return (df["close"] - lower) / (upper - lower)


# ---------- Realized Volatility ----------
class RealizedVol20(Feature):
    name = "spy.realized_vol_20"
    definition = "20-session realized volatility (annualized)"
    formula = "sqrt(252) * std(log_return, 20, ddof=0)"
    input_fields = ["SPY.close"]
    lookback = 21
    unit = "annualized vol"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        log_ret = np.log(df["close"] / df["close"].shift(1))
        return np.sqrt(252) * log_ret.rolling(20).std(ddof=0)


# ---------- Gap ----------
class Gap1D(Feature):
    name = "spy.gap_1d"
    definition = "1-session opening gap"
    formula = "open_t / close_{t-1} - 1"
    input_fields = ["SPY.open", "SPY.close"]
    lookback = 2
    unit = "ratio"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["open"] / df["close"].shift(1) - 1


# ---------- Volume Z-score ----------
class VolumeZScore20(Feature):
    name = "spy.volume_zscore_20"
    definition = "20-session volume z-score (population std)"
    formula = "(volume - mean(volume,20)) / std(volume,20,ddof=0)"
    input_fields = ["SPY.volume"]
    lookback = 20
    unit = "z-score"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["volume"].rolling(20).mean()
        s = df["volume"].rolling(20).std(ddof=0)
        return (df["volume"] - m) / s


# ---------- Trend Slope (linear regression) ----------
def _make_slope(n: int) -> type[Feature]:
    class _Slope(Feature):
        name = f"spy.close_slope_{n}"
        definition = f"linear regression slope of close over last {n} sessions"
        formula = f"slope = cov(x, close[t-{n}+1:t]) / var(x), x = 0..{n}-1"
        input_fields = ["SPY.close"]
        lookback = n
        unit = "price/session"

        def compute(self, df: pd.DataFrame) -> pd.Series:
            x = np.arange(n)
            return df["close"].rolling(n).apply(
                lambda y: np.polyfit(x, y, 1)[0], raw=True)
    _Slope.__name__ = f"CloseSlope{n}"
    return _Slope


CloseSlope20, CloseSlope50 = _make_slope(20), _make_slope(50)
