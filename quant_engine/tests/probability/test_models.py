# -*- coding: utf-8 -*-
"""Probability 模型测试。"""
import pytest

from quant_engine.probability.models import ProbabilityEstimate


def _est(**kw):
    base = dict(symbol="SPY", observation_time="2024-06-03T16:00:00", as_of="2024-06-03T23:59:59",
                horizon="T+1", p_up=0.4, p_flat=0.3, p_down=0.3, sample_size=100,
                evidence_level=5, method="unconditional", probability_version="v1")
    base.update(kw)
    return ProbabilityEstimate(**base)


def test_valid_probability():
    est = _est()
    assert est.p_up + est.p_flat + est.p_down == pytest.approx(1.0, abs=1e-9)


def test_sum_must_equal_one():
    with pytest.raises(ValueError):
        _est(p_up=0.5, p_flat=0.4, p_down=0.4)


def test_probability_must_be_in_range():
    with pytest.raises(ValueError):
        _est(p_up=1.2, p_flat=-0.1, p_down=-0.1)
