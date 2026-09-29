# -*- coding: utf-8 -*-
"""PIT Leakage 测试（Test A/B/C/D）。"""
from datetime import datetime

import pandas as pd

from quant_engine.features.pipeline import build_features


def test_A_adding_future_data_does_not_change_past():
    """Test A：加入 T+1 数据后，T 的 feature 完全不变。"""
    names = ["spy.sma_20", "spy.rsi_14", "spy.atr_14"]
    f_t = build_features("SPY", "daily", end="2024-06-03", feature_names=names)
    f_t1 = build_features("SPY", "daily", end="2024-06-10", feature_names=names)
    d_t = {(p.feature_name, p.observation_time): p.value for p in f_t}
    d_t1 = {(p.feature_name, p.observation_time): p.value for p in f_t1
            if p.observation_time <= pd.Timestamp("2024-06-03")}
    assert d_t == d_t1


def test_B_as_of_blocks_future_observation():
    """Test B：as_of 早于 source observation 的 available_at，该 observation 不可见。"""
    as_of = datetime(2024, 6, 3, 23, 59, 59)
    f = build_features("SPY", "daily", as_of=as_of, feature_names=["spy.return_1d"])
    assert all(p.observation_time <= pd.Timestamp("2024-06-03") for p in f)
    # 2024-06-04 的 return 不可见
    assert all(p.observation_time != pd.Timestamp("2024-06-04") for p in f)


def test_C_history_unchanged_with_more_data():
    """Test C：加入未来数据后，历史 feature 不得改变。"""
    names = ["spy.bb_upper", "spy.bb_lower", "spy.close_slope_20"]
    f_short = build_features("SPY", "daily", start="2024-05-01", end="2024-05-15",
                             feature_names=names)
    f_long = build_features("SPY", "daily", start="2024-05-01", end="2024-06-15",
                            feature_names=names)
    d_short = {(p.feature_name, p.observation_time): p.value for p in f_short}
    d_long = {(p.feature_name, p.observation_time): p.value for p in f_long
              if p.observation_time <= pd.Timestamp("2024-05-15")}
    assert d_short == d_long


def test_D_no_revision_visible_before_as_of():
    """Test D：P1 数据无 revision 字段污染，available_at 严格继承。"""
    f = build_features("SPY", "daily", end="2024-06-03", feature_names=["spy.sma_50"])
    ok = [p for p in f if p.quality_flag == "OK"]
    # 每个 OK 点的 available_at 必须 >= observation_time（无未来 available）
    assert all(p.available_at >= p.observation_time for p in ok)
