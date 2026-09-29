# -*- coding: utf-8 -*-
"""Regime Engine 端到端测试。"""
import pandas as pd

from quant_engine.regimes import compute_regime


def test_compute_regime_returns_state():
    s = compute_regime("SPY", "2024-06-03")
    assert s.symbol == "SPY"
    assert s.observation_time.date() == pd.Timestamp("2024-06-03").date()
    assert s.overall_status() in ("OK", "PARTIAL", "NOT_AVAILABLE")
    assert s.regime_version == "v1"
    assert s.source_feature_versions == ["p2_v1"]
    assert s.source_event_versions == ["p3_v1"]
