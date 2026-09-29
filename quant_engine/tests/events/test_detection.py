# -*- coding: utf-8 -*-
"""Event Detection 正确性测试（用已知历史事实验证）。"""
import pandas as pd

from quant_engine.events import detect_events


def _dates(events):
    return {pd.Timestamp(e.observation_time).date() for e in events}


def test_large_down_day_2020_03_16():
    evs = detect_events("SPY", ["large_down_day"], start="2020-03-10", end="2020-03-17")
    assert pd.Timestamp("2020-03-16").date() in _dates(evs)


def test_large_up_day_2020_03_24():
    evs = detect_events("SPY", ["large_up_day"], start="2020-03-18", end="2020-03-25")
    assert pd.Timestamp("2020-03-24").date() in _dates(evs)


def test_cross_event_requires_shift():
    # cross 事件需要前一日数据（shift），单日窗口应无 cross
    evs = detect_events("SPY", ["price_cross_sma20"], start="2024-06-03", end="2024-06-03")
    assert len(evs) == 0
