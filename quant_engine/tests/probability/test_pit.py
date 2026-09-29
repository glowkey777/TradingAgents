# -*- coding: utf-8 -*-
"""Probability PIT / Leakage 测试（Test A/B/C/D/E）。"""
from datetime import datetime

import pandas as pd
import pytest

from quant_engine.probability.estimator import estimate
from quant_engine.probability.models import ProbabilityDefinition
from quant_engine.probability.registry import ProbabilityRegistry
from quant_engine.probability.validation import no_label_in_inputs, no_future_leak, probability_valid


def _hist(n=40):
    idx = pd.date_range("2024-01-01", periods=n)
    return pd.DataFrame({
        "trend": ["bull_trend"] * n, "volatility": ["low_volatility"] * n,
        "macro": ["normal_macro"] * n, "events": [set()] * n,
        "label_t1": (["UP"] * (n // 2)) + (["DOWN"] * (n - n // 2)),
    }, index=idx)


def _def(method="unconditional"):
    return ProbabilityDefinition(probability_name="t", method=method, inputs=[],
                                 horizon="T+1", alpha=1.0)


def test_A_future_data_does_not_change_estimate():
    h = _hist()
    d = _def()
    a = estimate(h, {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 3, 2))
    b = estimate(h, {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 6, 1))
    assert a.p_up == b.p_up and a.p_flat == b.p_flat and a.p_down == b.p_down


def test_C_no_label_in_inputs():
    for d in ProbabilityRegistry.all():
        assert no_label_in_inputs(d), f"{d.probability_name} 输入含 label/future"


def test_D_probability_valid():
    h = _hist()
    d = _def()
    est = estimate(h, {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 3, 2))
    assert probability_valid(est)
    assert no_future_leak(est)


def test_E_deterministic():
    h = _hist()
    d = _def()
    a = estimate(h, {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 3, 2))
    b = estimate(h, {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 3, 2))
    assert (a.p_up, a.p_flat, a.p_down) == (b.p_up, b.p_flat, b.p_down)


def test_B_missing_label_excluded():
    h = _hist()
    h.loc[h.index[0], "label_t1"] = None  # 删未来 label
    d = _def()
    est = estimate(h, {}, d, "T+1", datetime(2024, 3, 1), datetime(2024, 3, 2))
    assert est.sample_size == 39  # 缺 label 的历史样本被排除
