# -*- coding: utf-8 -*-
"""Evidence Engine 测试。"""
from quant_engine.probability import build_history_table


def test_history_table_built():
    h = build_history_table("2013-01-01", "2026-09-25")
    assert len(h) > 3000
    for col in ["trend", "volatility", "macro", "events", "label_t1", "label_t2"]:
        assert col in h.columns


def test_label_distribution_nonempty():
    h = build_history_table("2013-01-01", "2026-09-25")
    assert set(h["label_t1"].dropna().unique()) <= {"UP", "FLAT", "DOWN"}
