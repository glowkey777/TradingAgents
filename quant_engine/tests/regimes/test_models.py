# -*- coding: utf-8 -*-
"""Regime 模型测试。"""
from quant_engine.regimes.models import RegimeState, PROBABILITY_TYPE


def test_state_is_multidimensional_not_string():
    from quant_engine.regimes import compute_regime
    s = compute_regime("SPY", "2024-06-03")
    assert isinstance(s.trend, dict) and "bull_trend" in s.trend
    assert isinstance(s.volatility, dict)
    assert isinstance(s.macro, dict)
    assert isinstance(s.event, dict)
    assert s.probability_type == PROBABILITY_TYPE


def test_each_dimension_sums_to_one():
    from quant_engine.regimes import compute_regime
    s = compute_regime("SPY", "2024-06-03")
    for d in (s.trend, s.volatility, s.macro, s.event):
        if d:
            assert abs(sum(d.values()) - 1) < 1e-9
