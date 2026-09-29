# -*- coding: utf-8 -*-
"""Estimator 测试：Laplace smoothing + fallback。"""
from datetime import datetime

import pandas as pd
import pytest

from quant_engine.probability.estimator import estimate, _laplace
from quant_engine.probability.models import ProbabilityDefinition


def test_laplace_smoothing_manual():
    p = _laplace({"UP": 9, "FLAT": 5, "DOWN": 4}, alpha=1.0)
    assert p["UP"] == pytest.approx(10 / 21, abs=1e-9)
    assert p["FLAT"] == pytest.approx(6 / 21, abs=1e-9)
    assert p["DOWN"] == pytest.approx(5 / 21, abs=1e-9)


def _hist():
    idx = pd.date_range("2024-01-01", periods=40)
    return pd.DataFrame({
        "trend": ["bull_trend"] * 40,
        "volatility": ["low_volatility"] * 40,
        "macro": ["normal_macro"] * 40,
        "events": [set()] * 40,
        "label_t1": ["UP"] * 20 + ["DOWN"] * 20,
    }, index=idx)


def test_estimate_unconditional():
    d = ProbabilityDefinition(probability_name="t", method="unconditional", inputs=[],
                              horizon="T+1", alpha=1.0)
    est = estimate(_hist(), {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 3, 2))
    assert est.evidence_level == 5
    assert est.sample_size == 40
    assert est.status == "LOW_SAMPLE"  # 30 <= 40 < 100
    assert abs(est.p_up + est.p_flat + est.p_down - 1) < 1e-9


def test_estimate_insufficient_sample():
    small = _hist().iloc[:10]
    d = ProbabilityDefinition(probability_name="t", method="unconditional", inputs=[],
                              horizon="T+1", alpha=1.0)
    est = estimate(small, {}, d, "T+1", datetime(2024, 1, 20), datetime(2024, 1, 21))
    assert est.status == "INSUFFICIENT_SAMPLE"
