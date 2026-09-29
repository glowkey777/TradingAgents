# -*- coding: utf-8 -*-
"""Trend Regime 测试。"""
from quant_engine.regimes import compute_regime


def test_bull_2024_06_03():
    s = compute_regime("SPY", "2024-06-03")
    assert s.trend["bull_trend"] > 0.5
    assert s.trend["bear_trend"] < 0.1


def test_bear_2020_03_16():
    s = compute_regime("SPY", "2020-03-16")
    assert s.trend["bear_trend"] > 0.5
    assert s.trend["bull_trend"] < 0.5


def test_trend_sums_to_one():
    s = compute_regime("SPY", "2024-06-03")
    assert abs(sum(s.trend.values()) - 1) < 1e-9
