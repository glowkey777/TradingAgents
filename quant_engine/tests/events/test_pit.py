# -*- coding: utf-8 -*-
"""Event PIT 测试（Test A/B）。"""
from datetime import datetime

import pandas as pd

from quant_engine.events import detect_events


def test_A_as_of_blocks_future_event():
    as_of = datetime(2024, 6, 3, 23, 59, 59)
    evs = detect_events("SPY", ["large_down_day"], start="2024-06-01",
                        end="2024-06-10", as_of=as_of)
    assert all(pd.Timestamp(e.observation_time) <= pd.Timestamp("2024-06-03") for e in evs)


def test_B_adding_future_data_does_not_change_past_events():
    before = detect_events("SPY", ["large_down_day"], start="2024-01-01", end="2024-06-03")
    after = detect_events("SPY", ["large_down_day"], start="2024-01-01", end="2024-06-10")
    past_after = [e for e in after if pd.Timestamp(e.observation_time) <= pd.Timestamp("2024-06-03")]
    assert len(before) == len(past_after)
    b = {e.observation_time: e.event_value for e in before}
    a = {e.observation_time: e.event_value for e in past_after}
    assert b == a
