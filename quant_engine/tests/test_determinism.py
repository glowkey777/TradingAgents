# -*- coding: utf-8 -*-
"""Determinism 测试：同输入 → 同输出。"""
from quant_engine.features.pipeline import build_features


def _signature(pts):
    return [(p.feature_name, str(p.observation_time), p.value, p.quality_flag) for p in pts]


def test_daily_deterministic():
    a = build_features("SPY", "daily", start="2024-01-01", end="2024-06-03")
    b = build_features("SPY", "daily", start="2024-01-01", end="2024-06-03")
    assert _signature(a) == _signature(b)


def test_intraday_deterministic():
    a = build_features("SPY", "15m", start="2024-06-03", end="2024-06-03")
    b = build_features("SPY", "15m", start="2024-06-03", end="2024-06-03")
    assert _signature(a) == _signature(b)


def test_macro_deterministic():
    a = build_features("SPY", "daily", start="2024-01-01", end="2024-06-03",
                       feature_names=["macro.vix_zscore_20", "macro.us10y_us5y_spread"])
    b = build_features("SPY", "daily", start="2024-01-01", end="2024-06-03",
                       feature_names=["macro.vix_zscore_20", "macro.us10y_us5y_spread"])
    assert _signature(a) == _signature(b)
