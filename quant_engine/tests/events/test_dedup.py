# -*- coding: utf-8 -*-
"""Event De-duplication 测试。"""
import pandas as pd

from quant_engine.events import detect_events
from quant_engine.events.validation import deduplicate


def test_first_trigger_only_removes_consecutive():
    raw = detect_events("SPY", ["above_sma_20"], start="2013-01-01", end="2026-09-25")
    deduped = deduplicate(raw)
    assert len(deduped) <= len(raw)
    # 连续触发已被去重（相邻 5 session 内只保留一个）
    for e in deduped:
        ts = pd.Timestamp(e.observation_time)
        others = [pd.Timestamp(x.observation_time) for x in deduped
                  if x.event_name == e.event_name and x is not e]
        assert all(abs((ts - o).days) > 5 for o in others)


def test_dedup_deterministic():
    raw = detect_events("SPY", ["vix_shock_up"], start="2020-01-01", end="2024-06-03")
    d1 = deduplicate(raw)
    d2 = deduplicate(raw)
    assert [e.observation_time for e in d1] == [e.observation_time for e in d2]
