# -*- coding: utf-8 -*-
"""Macro Feature 测试。"""
import pandas as pd
import pytest

from quant_engine.features.base import load_macro_wide
from quant_engine.features.pipeline import build_features


def test_vix_zscore_independent():
    m = load_macro_wide()
    s = m["vix"]
    manual = (s - s.rolling(20).mean()) / s.rolling(20).std(ddof=0)
    p = build_features("SPY", "daily", start="2024-05-01", end="2024-06-03",
                       feature_names=["macro.vix_zscore_20"])
    val = {x.observation_time: x.value for x in p if x.quality_flag == "OK"}
    ts = pd.Timestamp("2024-06-03")
    assert val[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_yield_spread_independent():
    m = load_macro_wide()
    manual = m["us10y"] - m["us5y"]
    p = build_features("SPY", "daily", start="2024-05-01", end="2024-06-03",
                       feature_names=["macro.us10y_us5y_spread"])
    val = {x.observation_time: x.value for x in p if x.quality_flag == "OK"}
    ts = pd.Timestamp("2024-06-03")
    assert val[ts] == pytest.approx(manual.loc[ts], abs=1e-6)


def test_macro_change_no_lookahead():
    m = load_macro_wide()
    s = m["vix"]
    manual = s / s.shift(5) - 1
    p = build_features("SPY", "daily", start="2024-05-01", end="2024-06-03",
                       feature_names=["macro.vix_change_5d"])
    val = {x.observation_time: x.value for x in p if x.quality_flag == "OK"}
    ts = pd.Timestamp("2024-06-03")
    assert val[ts] == pytest.approx(manual.loc[ts], abs=1e-6)
