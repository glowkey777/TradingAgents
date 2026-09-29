# -*- coding: utf-8 -*-
"""Determinism 测试。"""
from datetime import datetime

import pandas as pd

from quant_engine.probability.estimator import estimate
from quant_engine.probability.models import ProbabilityDefinition


def test_deterministic_estimate():
    idx = pd.date_range("2024-01-01", periods=60)
    h = pd.DataFrame({
        "trend": ["bull_trend"] * 60, "volatility": ["low_volatility"] * 60,
        "macro": ["normal_macro"] * 60, "events": [set()] * 60,
        "label_t1": ["UP"] * 30 + ["FLAT"] * 20 + ["DOWN"] * 10,
    }, index=idx)
    d = ProbabilityDefinition(probability_name="t", method="unconditional", inputs=[],
                              horizon="T+1", alpha=1.0)
    a = estimate(h, {}, d, "T+1", datetime(2024, 4, 1), datetime(2024, 4, 2))
    b = estimate(h, {}, d, "T+1", datetime(2024, 4, 1), datetime(2024, 4, 2))
    assert (a.p_up, a.p_flat, a.p_down, a.evidence_level, a.sample_size) == \
           (b.p_up, b.p_flat, b.p_down, b.evidence_level, b.sample_size)
