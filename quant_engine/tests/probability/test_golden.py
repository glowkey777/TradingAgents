# -*- coding: utf-8 -*-
"""Probability Golden Regression：锁定固定条件分布的 Laplace 平滑值。"""
from datetime import datetime

import pandas as pd
import pytest

from quant_engine.probability.estimator import estimate
from quant_engine.probability.models import ProbabilityDefinition


def _hist():
    idx = pd.date_range("2024-01-01", periods=40)
    return pd.DataFrame({
        "trend": ["bull_trend"] * 40, "volatility": ["low_volatility"] * 40,
        "macro": ["normal_macro"] * 40, "events": [set()] * 40,
        "label_t1": ["UP"] * 20 + ["DOWN"] * 20,
    }, index=idx)


def test_golden_unconditional_laplace():
    d = ProbabilityDefinition(probability_name="t", method="unconditional", inputs=[],
                              horizon="T+1", alpha=1.0)
    est = estimate(_hist(), {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 3, 2))
    assert est.p_up == pytest.approx(21 / 43, abs=1e-9)     # (20+1)/(40+3)
    assert est.p_flat == pytest.approx(1 / 43, abs=1e-9)    # (0+1)/43
    assert est.p_down == pytest.approx(21 / 43, abs=1e-9)   # (20+1)/43
    assert est.evidence_level == 5
