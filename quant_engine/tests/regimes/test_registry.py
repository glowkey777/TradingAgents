# -*- coding: utf-8 -*-
"""Regime Registry 测试。"""
from quant_engine.regimes import RegimeRegistry


def test_four_dimensions():
    dims = RegimeRegistry.dimensions()
    assert {d.dimension for d in dims} == {"trend", "volatility", "macro", "event"}


def test_all_dimensions_versioned():
    for d in RegimeRegistry.dimensions():
        assert d.version
        assert d.states
        assert d.probability_type == "RULE_BASED_REGIME_SCORE"


def test_all_rules_versioned():
    for r in RegimeRegistry.rules():
        assert r.version
        assert r.dimension in {"trend", "volatility", "macro", "event"}
        assert r.condition
