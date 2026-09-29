# -*- coding: utf-8 -*-
"""Sample-size gate 测试。"""
from datetime import datetime

import pandas as pd

from quant_engine.probability.estimator import estimate
from quant_engine.probability.models import ProbabilityDefinition


def _hist(n):
    idx = pd.date_range("2024-01-01", periods=n)
    return pd.DataFrame({
        "trend": ["bull_trend"] * n, "volatility": ["low_volatility"] * n,
        "macro": ["normal_macro"] * n, "events": [set()] * n,
        "label_t1": ["UP"] * n,
    }, index=idx)


def _est(n):
    d = ProbabilityDefinition(probability_name="t", method="unconditional", inputs=[],
                              horizon="T+1", alpha=1.0)
    return estimate(_hist(n), {}, d, "T+1", datetime(2024, 2, 1), datetime(2024, 2, 2))


def test_insufficient_below_30():
    assert _est(10).status == "INSUFFICIENT_SAMPLE"


def test_low_between_30_and_100():
    assert _est(50).status == "LOW_SAMPLE"


def test_valid_at_100():
    assert _est(100).status == "VALID"
