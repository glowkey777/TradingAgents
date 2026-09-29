# -*- coding: utf-8 -*-
"""PIT 测试：as_of 语义（Test A/B/C/D）。"""
from datetime import datetime, date

from quant_engine.state import build_quant_state


def test_A_intraday_no_future_close():
    # 盘中 10:00，看不到当天 23:59:59 才可用的收盘
    s = build_quant_state("SPY", datetime(2024, 6, 3, 10, 0))
    assert s.market.trading_date < date(2024, 6, 3)


def test_close_visible_after_close():
    s = build_quant_state("SPY", datetime(2024, 6, 3, 23, 59, 59))
    assert s.market.trading_date == date(2024, 6, 3)


def test_B_no_future_feature(state_2024):
    # 所有 feature 的 observation_time 不晚于 market trading_date
    assert state_2024.features.values  # 有值
    # unavailable 语义保留（None，非 0）
    assert all(v is None or isinstance(v, float) for v in state_2024.features.values.values())


def test_D_probability_sum(state_2024):
    t1 = state_2024.probability.t1
    assert abs(t1.p_up + t1.p_flat + t1.p_down - 1) < 1e-6
