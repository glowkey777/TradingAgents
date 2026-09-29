# -*- coding: utf-8 -*-
"""Missing Data 语义测试（NOT_AVAILABLE / INSUFFICIENT_DATA，非 silent zero）。"""
from quant_engine.regimes import compute_regime


def test_early_boundary_not_available():
    s = compute_regime("SPY", "2013-01-02")
    assert s.status["trend"] == "NOT_AVAILABLE"
    assert s.overall_status() == "PARTIAL"


def test_no_silent_zero_fill():
    # trend 无数据 → 空 dict，而不是 {bull:0, bear:0, range:0}（避免隐性污染）
    s = compute_regime("SPY", "2013-01-02")
    assert s.trend == {}
