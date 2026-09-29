# -*- coding: utf-8 -*-
"""Regime Determinism 测试。"""
from quant_engine.regimes import compute_regime


def test_deterministic():
    a = compute_regime("SPY", "2024-06-03")
    b = compute_regime("SPY", "2024-06-03")
    assert a.trend == b.trend
    assert a.volatility == b.volatility
    assert a.macro == b.macro
    assert a.event == b.event
    assert a.confidence == b.confidence
