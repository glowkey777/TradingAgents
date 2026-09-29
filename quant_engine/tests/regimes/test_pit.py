# -*- coding: utf-8 -*-
"""Regime PIT / Leakage 测试（Test A/B/C/D/E）。"""
from datetime import datetime

from quant_engine.regimes import compute_regime
from quant_engine.regimes.validation import no_label_contamination


def test_A_future_data_does_not_change_regime():
    a = compute_regime("SPY", "2024-06-03", as_of=datetime(2024, 6, 3, 23, 59, 59))
    b = compute_regime("SPY", "2024-06-03", as_of=datetime(2024, 6, 10, 23, 59, 59))
    assert a.trend == b.trend
    assert a.volatility == b.volatility
    assert a.macro == b.macro


def test_B_delete_future_still_generates():
    s = compute_regime("SPY", "2024-06-03", as_of=datetime(2024, 6, 3, 23, 59, 59))
    assert s.overall_status() in ("OK", "PARTIAL")


def test_C_no_label_in_regime():
    s = compute_regime("SPY", "2024-06-03")
    assert no_label_contamination(s)


def test_D_future_event_does_not_change_regime():
    a = compute_regime("SPY", "2024-06-03", as_of=datetime(2024, 6, 3, 23, 59, 59))
    b = compute_regime("SPY", "2024-06-03", as_of=datetime(2024, 6, 10, 23, 59, 59))
    assert a.event == b.event


def test_E_same_input_same_output():
    a = compute_regime("SPY", "2024-06-03")
    b = compute_regime("SPY", "2024-06-03")
    assert a.trend == b.trend and a.volatility == b.volatility
    assert a.macro == b.macro and a.event == b.event
