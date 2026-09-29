# -*- coding: utf-8 -*-
"""Label Horizons 测试：future_return 正确（T+1 / T+2）。"""
import pandas as pd
import pytest

from quant_engine.labels import generate_labels, LABEL_DEFINITIONS
from quant_engine.features.base import load_wide


def test_t1_future_return_correct():
    close = load_wide("daily")["close"]
    idx = list(close.index)
    recs = generate_labels("SPY", LABEL_DEFINITIONS["t1_up_flat_down"],
                           start="2024-01-01", end="2024-06-03")
    for l in recs[:20]:
        ts = pd.Timestamp(l.observation_time)
        i = idx.index(ts)
        expected = close.iloc[i + 1] / close.iloc[i] - 1
        assert l.future_return == pytest.approx(expected, abs=1e-9)


def test_t2_future_return_correct():
    close = load_wide("daily")["close"]
    idx = list(close.index)
    recs = generate_labels("SPY", LABEL_DEFINITIONS["t2_up_flat_down"],
                           start="2024-01-01", end="2024-06-03")
    for l in recs[:20]:
        ts = pd.Timestamp(l.observation_time)
        i = idx.index(ts)
        expected = close.iloc[i + 2] / close.iloc[i] - 1
        assert l.future_return == pytest.approx(expected, abs=1e-9)
