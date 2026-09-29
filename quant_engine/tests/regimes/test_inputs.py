# -*- coding: utf-8 -*-
"""Regime Input 测试。"""
from quant_engine.regimes.inputs import collect_features, FEATURE_NAMES


def test_collect_features_2024_06_03():
    f = collect_features("SPY", "2024-06-03", None)
    assert f["spy.distance_to_sma_20"] is not None
    assert f["spy.sma_200"] is not None
    assert f["vix_level"] is not None
    assert f["spy.realized_vol_20"] is not None


def test_collect_features_early_boundary_not_available():
    # 2013-01-02 是数据起点，warm-up 不足 → sma_200 为 None
    f = collect_features("SPY", "2013-01-02", None)
    assert f["spy.sma_200"] is None
