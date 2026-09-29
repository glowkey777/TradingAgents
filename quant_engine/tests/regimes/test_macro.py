# -*- coding: utf-8 -*-
"""Macro Regime 测试。"""
from quant_engine.regimes import compute_regime


def test_macro_shock_2020_03_16():
    s = compute_regime("SPY", "2020-03-16")
    assert s.macro["macro_shock"] > 0.5


def test_normal_macro_2024_06_03():
    s = compute_regime("SPY", "2024-06-03")
    assert s.macro["normal_macro"] > 0.5


def test_macro_sums_to_one():
    s = compute_regime("SPY", "2024-06-03")
    assert abs(sum(s.macro.values()) - 1) < 1e-9
