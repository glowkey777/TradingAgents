# -*- coding: utf-8 -*-
"""Label Generation 测试。"""
import pandas as pd

from quant_engine.labels import generate_labels, LABEL_DEFINITIONS


def test_generate_t1():
    recs = generate_labels("SPY", LABEL_DEFINITIONS["t1_up_flat_down"],
                           start="2024-01-01", end="2024-06-03")
    assert len(recs) > 0
    assert all(l.label in ("UP", "FLAT", "DOWN") for l in recs)


def test_missing_future_endpoint_not_flat():
    # 数据末尾：最后交易日 2026-09-25 无 T+1 → 不生成 label（unavailable），非 FLAT
    recs = generate_labels("SPY", LABEL_DEFINITIONS["t1_up_flat_down"],
                           start="2026-09-01", end="2026-09-25")
    obs = {l.observation_time.date() for l in recs}
    assert pd.Timestamp("2026-09-25").date() not in obs
