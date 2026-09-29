# -*- coding: utf-8 -*-
"""Label Determinism 测试。"""
from quant_engine.labels import generate_labels, LABEL_DEFINITIONS


def test_label_deterministic():
    d = LABEL_DEFINITIONS["t1_up_flat_down"]
    a = generate_labels("SPY", d, start="2024-01-01", end="2024-06-03")
    b = generate_labels("SPY", d, start="2024-01-01", end="2024-06-03")
    sa = [(l.observation_time, l.future_return, l.threshold, l.label) for l in a]
    sb = [(l.observation_time, l.future_return, l.threshold, l.label) for l in b]
    assert sa == sb
