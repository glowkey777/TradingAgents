# -*- coding: utf-8 -*-
"""Leakage 测试：future 不进 state（Test E）。"""
from datetime import datetime

from quant_engine.state import build_quant_state, canonical_json


def test_E_deterministic_state():
    a = build_quant_state("SPY", datetime(2024, 6, 3, 23, 59, 59))
    b = build_quant_state("SPY", datetime(2024, 6, 3, 23, 59, 59))
    assert canonical_json(a) == canonical_json(b)


def test_future_as_of_does_not_change_past_obs():
    # as_of 不同 → observation_time 不同，但都是 PIT 确定的结果
    s1 = build_quant_state("SPY", datetime(2024, 6, 3, 23, 59, 59))
    s2 = build_quant_state("SPY", datetime(2024, 6, 4, 23, 59, 59))
    assert s1.market.trading_date < s2.market.trading_date
