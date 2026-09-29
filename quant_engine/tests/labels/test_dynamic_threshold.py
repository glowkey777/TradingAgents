# -*- coding: utf-8 -*-
"""Dynamic Threshold 测试：threshold = k × realized_vol / sqrt(252)。"""
from math import sqrt

import pandas as pd
import pytest

from quant_engine.labels import generate_labels, LABEL_DEFINITIONS
from quant_engine.features.pipeline import build_features


def test_threshold_equals_k_times_daily_vol():
    k = LABEL_DEFINITIONS["t1_up_flat_down"].threshold_multiplier
    recs = generate_labels("SPY", LABEL_DEFINITIONS["t1_up_flat_down"],
                           start="2024-01-01", end="2024-06-03")
    rv = {pd.Timestamp(p.observation_time): p.value
          for p in build_features("SPY", "daily", start="2024-01-01", end="2024-06-03",
                                  feature_names=["spy.realized_vol_20"])
          if p.quality_flag == "OK"}
    for l in recs[:50]:
        expected = k * rv[pd.Timestamp(l.observation_time)] / sqrt(252)
        assert l.threshold == pytest.approx(expected, abs=1e-12)
