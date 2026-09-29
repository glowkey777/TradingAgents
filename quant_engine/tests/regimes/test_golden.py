# -*- coding: utf-8 -*-
"""Regime Golden Regression：锁定固定日期的多维 regime 值。"""
import pytest

from quant_engine.regimes import compute_regime


def _regime(day):
    s = compute_regime("SPY", day)
    return s


def test_golden_2020_03_16():
    s = _regime("2020-03-16")
    assert s.trend["bear_trend"] == pytest.approx(0.8, abs=1e-9)
    assert s.trend["bull_trend"] == pytest.approx(0.2, abs=1e-9)
    assert s.volatility["high_volatility"] == pytest.approx(1.0, abs=1e-9)
    assert s.macro["macro_shock"] == pytest.approx(0.75, abs=1e-9)
    assert s.event["event_driven"] == pytest.approx(0.909091, abs=1e-6)


def test_golden_2024_06_03():
    s = _regime("2024-06-03")
    assert s.trend["bull_trend"] == pytest.approx(5 / 6, abs=1e-9)
    assert s.trend["range"] == pytest.approx(1 / 6, abs=1e-9)
    assert s.volatility["low_volatility"] == pytest.approx(1.0, abs=1e-9)
    assert s.macro["normal_macro"] == pytest.approx(1.0, abs=1e-9)
    assert s.event["normal_event"] == pytest.approx(1.0, abs=1e-9)
