# -*- coding: utf-8 -*-
"""Volatility Regime 测试。"""
from quant_engine.regimes import compute_regime


def test_high_vol_2020_03_16():
    s = compute_regime("SPY", "2020-03-16")
    assert s.volatility["high_volatility"] > 0.9


def test_low_vol_2024_06_03():
    s = compute_regime("SPY", "2024-06-03")
    assert s.volatility["low_volatility"] > 0.5


def test_volatility_sums_to_one():
    s = compute_regime("SPY", "2024-06-03")
    assert abs(sum(s.volatility.values()) - 1) < 1e-9
