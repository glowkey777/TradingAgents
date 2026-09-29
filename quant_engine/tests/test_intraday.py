# -*- coding: utf-8 -*-
"""Intraday Feature 测试：15m / session / 30m 聚合。"""
import pandas as pd
import pytest

from quant_engine.features.base import load_wide
from quant_engine.features.intraday import resample_ohlcv
from quant_engine.features.pipeline import build_features


def test_15m_return_first_bar_is_na():
    p = build_features("SPY", "15m", start="2024-06-03", end="2024-06-03",
                       feature_names=["spy_15m.return"])
    ok = [x for x in p if x.quality_flag == "OK"]
    # 首 bar（09:45）return 是 NaN（无前一天 bar）
    assert all(x.observation_time != pd.Timestamp("2024-06-03 09:45") for x in ok)


def test_session_return_independent():
    wide = load_wide("15m")
    day = wide.loc["2024-06-03"]
    manual = day["close"].iloc[-1] / day["close"].iloc[0] - 1
    p = build_features("SPY", "session", start="2024-06-03", end="2024-06-03",
                       feature_names=["spy_session.return"])
    val = [x.value for x in p if x.quality_flag == "OK"][0]
    assert val == pytest.approx(manual, abs=1e-9)


def test_vwap_between_high_low():
    p = build_features("SPY", "15m", start="2024-06-03", end="2024-06-03",
                       feature_names=["spy_15m.vwap_session"])
    vals = [x.value for x in p if x.quality_flag == "OK"]
    day_high = load_wide("15m").loc["2024-06-03"]["high"].max()
    day_low = load_wide("15m").loc["2024-06-03"]["low"].min()
    # VWAP 必然在 day low 和 high 之间
    assert all(day_low - 1e-6 <= v <= day_high + 1e-6 for v in vals)


def test_30m_aggregation_ohlc():
    wide = load_wide("15m")
    day = wide.loc["2024-06-03"]
    res = resample_ohlcv(day, "30min")
    # 第一根 30m bar（10:00）的 open = 09:45 的 open
    first_15m_open = day.loc[day.index == "2024-06-03 09:45"]["open"].iloc[0]
    assert res["open"].iloc[0] == pytest.approx(first_15m_open, abs=1e-9)
    # 30m bar 的 high = 两根 15m bar 的 max
    bars = day.loc[day.index <= "2024-06-03 10:00"]
    assert res["high"].iloc[0] == pytest.approx(bars["high"].max(), abs=1e-9)
    assert res["close"].iloc[0] == pytest.approx(
        day.loc[day.index == "2024-06-03 10:00"]["close"].iloc[0], abs=1e-9)


def test_half_day_session_14_bars():
    wide = load_wide("15m")
    july3 = wide.loc["2024-07-03"]
    assert len(july3) == 14  # 半天交易日 14 bar
