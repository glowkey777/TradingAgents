# -*- coding: utf-8 -*-
"""Golden Feature 回归：锁定关键 feature 在固定日期的期望值。

以后任何代码/数据层修改，这些值必须不变（除非 feature_version 升级）。
"""
import pandas as pd
import pytest

from quant_engine.features.pipeline import build_features


def _val(feature, ts, freq="daily", start="2023-01-01", end="2024-06-03"):
    pts = build_features("SPY", freq, start=start, end=end, feature_names=[feature])
    return {p.observation_time: p.value for p in pts if p.quality_flag == "OK"}[pd.Timestamp(ts)]


GOLDEN = [
    ("spy.sma_20", "2024-06-03", 510.157287),
    ("spy.sma_50", "2024-06-03", 501.936592),
    ("spy.rsi_14", "2024-06-03", 58.438175),
    ("spy.atr_14", "2024-06-03", 4.902371),
    ("spy.macd_line", "2024-06-03", 3.782957),
    ("spy.bb_upper", "2024-06-03", 519.503549),
    ("spy.bb_lower", "2024-06-03", 500.811026),
    ("spy.realized_vol_20", "2024-06-03", 0.083970),
    ("spy.distance_to_sma_20", "2024-06-03", 0.004914),
    ("macro.vix_zscore_20", "2024-06-03", 0.328975),
    ("macro.us10y_us5y_spread", "2024-06-03", -0.015000),
]


@pytest.mark.parametrize("feature,ts,expected", GOLDEN)
def test_golden_feature(feature, ts, expected):
    assert _val(feature, ts) == pytest.approx(expected, abs=1e-4)


def test_golden_session_return():
    pts = build_features("SPY", "session", start="2024-06-03", end="2024-06-03",
                         feature_names=["spy_session.return"])
    v = [p.value for p in pts if p.quality_flag == "OK"][0]
    assert v == pytest.approx(-0.002, abs=1e-3)
