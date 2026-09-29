# -*- coding: utf-8 -*-
"""Probability Registry 测试。"""
from quant_engine.probability import ProbabilityRegistry


def test_baselines_registered():
    names = {d.probability_name for d in ProbabilityRegistry.all()}
    assert {"baseline_unconditional", "baseline_regime_conditional",
            "baseline_event_conditional", "baseline_hierarchical"} <= names


def test_definitions_versioned():
    for d in ProbabilityRegistry.all():
        assert d.version
        assert d.alpha > 0
        assert d.minimum_sample_size >= 30
