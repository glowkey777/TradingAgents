# -*- coding: utf-8 -*-
"""Label Golden Regression：锁定固定日期 label 的 future_return + label。

threshold 用 rolling vol（非递推），但 golden 仍固定 start 窗口保证可复现。
"""
import datetime

import pytest

from quant_engine.labels import generate_labels, LABEL_DEFINITIONS

START = "2013-01-01"
END = "2026-09-25"

GOLDEN = [
    ("T+1", "2020-03-16", 0.0539920784, "UP"),
    ("T+1", "2020-03-23", 0.0906032743, "UP"),
    ("T+1", "2024-06-03", 0.0011178477, "FLAT"),
    ("T+2", "2020-03-16", 0.0006253909, "FLAT"),
    ("T+2", "2020-03-23", 0.1069298049, "UP"),
    ("T+2", "2024-06-03", 0.0130162941, "UP"),
]


@pytest.mark.parametrize("horizon,day,fwd,label", GOLDEN)
def test_golden_label(horizon, day, fwd, label):
    key = "t1_up_flat_down" if horizon == "T+1" else "t2_up_flat_down"
    recs = generate_labels("SPY", LABEL_DEFINITIONS[key], start=START, end=END)
    d = {r.observation_time.date(): r for r in recs}
    r = d[datetime.date.fromisoformat(day)]
    assert r.future_return == pytest.approx(fwd, abs=1e-9)
    assert r.label == label
