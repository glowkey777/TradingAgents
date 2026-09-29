# -*- coding: utf-8 -*-
"""Event Regime 测试。"""
from quant_engine.regimes import compute_regime


def test_event_driven_2020_03_16():
    s = compute_regime("SPY", "2020-03-16")
    assert s.event["event_driven"] > 0.5


def test_normal_event_2024_06_03():
    s = compute_regime("SPY", "2024-06-03")
    assert s.event["normal_event"] > 0.9


def test_event_sums_to_one():
    s = compute_regime("SPY", "2024-06-03")
    assert abs(sum(s.event.values()) - 1) < 1e-9
