# -*- coding: utf-8 -*-
"""Leakage 测试：label 不得进入 similarity/normalization/regime/event。"""
from quant_engine.probability.registry import ProbabilityRegistry


def test_label_not_in_any_input():
    bad = {"future_return", "label"}
    for d in ProbabilityRegistry.all():
        for s in d.inputs:
            assert not (set(s.split()) & bad), f"{d.probability_name} 输入含 label"


def test_temporal_split_not_random():
    from quant_engine.probability import TEMPORAL_SPLIT
    assert TEMPORAL_SPLIT["train"][1] < TEMPORAL_SPLIT["validation"][0]
    assert TEMPORAL_SPLIT["validation"][1] < TEMPORAL_SPLIT["test"][0]
