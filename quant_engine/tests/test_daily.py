# -*- coding: utf-8 -*-
"""Daily Feature 独立计算验证（手算交叉验证，防止"自己测自己"）。"""
import numpy as np
import pandas as pd
import pytest

from quant_engine.features.base import load_wide
from quant_engine.features.pipeline import build_features


def _feat_dict(feature_names, start="2023-01-01", end="2024-06-03"):
    pts = build_features("SPY", "daily", start=start, end=end, feature_names=feature_names)
    return {p.observation_time: p.value for p in pts if p.quality_flag == "OK"}


def _close():
    return load_wide("daily")["close"]


def test_sma20_independent():
    close = _close()
    manual = close.rolling(20).mean()
    feat = _feat_dict(["spy.sma_20"])
    ts = pd.Timestamp("2024-06-03")
    assert feat[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_ema20_independent():
    close = _close()
    manual = close.ewm(span=20, adjust=False, min_periods=20).mean()
    feat = _feat_dict(["spy.ema_20"])
    ts = pd.Timestamp("2024-06-03")
    assert feat[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_rsi14_independent_wilder():
    close = _close()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss
    manual = 100 - 100 / (1 + rs)
    feat = _feat_dict(["spy.rsi_14"])
    ts = pd.Timestamp("2024-06-03")
    assert feat[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_atr14_independent_wilder():
    wide = load_wide("daily")
    prev_close = wide["close"].shift(1)
    tr = pd.concat([wide["high"] - wide["low"],
                    (wide["high"] - prev_close).abs(),
                    (wide["low"] - prev_close).abs()], axis=1).max(axis=1)
    manual = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    feat = _feat_dict(["spy.atr_14"])
    ts = pd.Timestamp("2024-06-03")
    assert feat[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_macd_line_independent():
    close = _close()
    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    manual = ema12 - ema26
    feat = _feat_dict(["spy.macd_line"])
    ts = pd.Timestamp("2024-06-03")
    assert feat[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_bollinger_upper_independent_population_std():
    close = _close()
    m = close.rolling(20).mean()
    s = close.rolling(20).std(ddof=0)
    manual = m + 2 * s
    feat = _feat_dict(["spy.bb_upper"])
    ts = pd.Timestamp("2024-06-03")
    assert feat[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_realized_vol_independent():
    close = _close()
    log_ret = np.log(close / close.shift(1))
    manual = np.sqrt(252) * log_ret.rolling(20).std(ddof=0)
    feat = _feat_dict(["spy.realized_vol_20"])
    ts = pd.Timestamp("2024-06-03")
    assert feat[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_no_lookahead_early_history_is_insufficient():
    pts = build_features("SPY", "daily", start="2024-01-01", end="2024-01-02",
                         feature_names=["spy.sma_200"])
    # 2 天数据不足以算 SMA200，全部 INSUFFICIENT_HISTORY
    assert all(p.quality_flag == "INSUFFICIENT_HISTORY" for p in pts)
