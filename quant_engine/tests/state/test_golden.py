# -*- coding: utf-8 -*-
"""Golden Regression：锁定 2024-06-03 + 2020-03-16（高波动）。"""
import pytest


def test_golden_2024_06_03(state_2024):
    s = state_2024
    assert s.market.trading_date.isoformat() == "2024-06-03"
    assert s.market.close == pytest.approx(512.66427201, rel=1e-6)
    # regime：bull 主导（2024 H1 牛势）
    assert s.regime.trend["bull_trend"] == pytest.approx(0.8333333333, abs=1e-6)
    assert s.regime.trend["bear_trend"] == pytest.approx(0.0, abs=1e-6)
    # probability T+1（hierarchical）
    assert s.probability.t1.p_up == pytest.approx(0.3210023866, abs=1e-6)
    assert s.probability.t1.evidence_level == 2


def test_golden_2020_03_16_crash(state_crash):
    s = state_crash
    assert s.market.trading_date.isoformat() == "2020-03-16"
    # 高波动：bear 主导 + high_volatility
    assert s.regime.trend["bear_trend"] > s.regime.trend["bull_trend"]
    assert s.regime.volatility["high_volatility"] == pytest.approx(1.0, abs=1e-6)
    assert s.data_quality.status in ("OK", "PARTIAL")
