# -*- coding: utf-8 -*-
"""Similarity 测试。"""
import pandas as pd

from quant_engine.probability.similarity import zscore_distance


def test_zscore_distance_returns_series():
    hist = pd.DataFrame({"f1": [1.0, 2.0, 3.0, 4.0, 5.0]},
                        index=pd.date_range("2024-01-01", periods=5))
    d = zscore_distance({"f1": 3.0}, hist, ["f1"])
    assert len(d) == 5
    assert not d.isna().any()
