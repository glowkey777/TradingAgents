# -*- coding: utf-8 -*-
"""Event Golden Regression：锁定事件检测值 + Event Study 统计。"""
import pandas as pd
import pytest

from quant_engine.events import detect_events, compute_forward_returns, summarize
from quant_engine.events.validation import deduplicate


def test_golden_event_value_2020_03_16():
    evs = detect_events("SPY", ["large_down_day"], start="2020-03-10", end="2020-03-17")
    vals = [e.event_value for e in evs
            if pd.Timestamp(e.observation_time).date() == pd.Timestamp("2020-03-16").date()]
    assert len(vals) == 1
    assert vals[0] == pytest.approx(-0.1094237338, abs=1e-9)


def test_golden_large_down_day_statistics():
    evs = deduplicate(detect_events("SPY", ["large_down_day"], start="2013-01-01", end="2026-09-25"))
    fwd = compute_forward_returns(evs, ["T+1", "T+2", "T+5"])
    s = summarize(fwd)
    d = {(r["horizon"]): r for _, r in s.iterrows()}
    assert d["T+1"]["N"] == 76
    assert d["T+1"]["mean"] == pytest.approx(0.0040326765, abs=1e-9)
    assert d["T+1"]["win_rate"] == pytest.approx(0.5921052632, abs=1e-9)
    assert d["T+5"]["mean"] == pytest.approx(0.0079120016, abs=1e-9)
    assert d["T+5"]["win_rate"] == pytest.approx(0.6184210526, abs=1e-9)
