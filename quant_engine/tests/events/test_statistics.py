# -*- coding: utf-8 -*-
"""Event Study 统计正确性测试。"""
import numpy as np

from quant_engine.events import detect_events, compute_forward_returns, summarize
from quant_engine.events.validation import deduplicate


def test_statistics_fields_complete():
    evs = deduplicate(detect_events("SPY", ["large_down_day"], start="2013-01-01", end="2026-09-25"))
    fwd = compute_forward_returns(evs, ["T+1"])
    stats = summarize(fwd)
    row = stats.iloc[0]
    for col in ["N", "mean", "median", "std", "win_rate", "min", "max", "p25", "p75"]:
        assert col in stats.columns
        assert not np.isnan(row[col])


def test_statistics_mean_manual():
    evs = deduplicate(detect_events("SPY", ["large_down_day"], start="2013-01-01", end="2026-09-25"))
    fwd = compute_forward_returns(evs, ["T+1"])
    vals = [f["forward_return"] for f in fwd]
    stats = summarize(fwd)
    assert stats.iloc[0]["mean"] == np.mean(vals)
    assert stats.iloc[0]["win_rate"] == np.mean([v > 0 for v in vals])
