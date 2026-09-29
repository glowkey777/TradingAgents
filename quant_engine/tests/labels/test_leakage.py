# -*- coding: utf-8 -*-
"""Label Leakage 测试（Test A/B/C/D）。"""
import pandas as pd

from quant_engine.labels import generate_labels, LABEL_DEFINITIONS
from quant_engine.features.pipeline import build_features
from quant_engine.features.registry import FeatureRegistry
from quant_engine.events.registry import EventRegistry


def test_A_features_unchanged_when_labels_added():
    f = ["spy.sma_20", "spy.rsi_14"]
    before = [(p.observation_time, p.value) for p in
              build_features("SPY", "daily", start="2024-01-01", end="2024-06-03", feature_names=f)]
    generate_labels("SPY", LABEL_DEFINITIONS["t1_up_flat_down"], start="2024-01-01", end="2024-06-03")
    after = [(p.observation_time, p.value) for p in
             build_features("SPY", "daily", start="2024-01-01", end="2024-06-03", feature_names=f)]
    assert before == after


def test_B_event_does_not_use_forward_return():
    bad = {"future_return", "label"}
    for d in EventRegistry.all():
        assert not (set(d.input_features) & bad), f"{d.event_name} 用了 label/forward"


def test_C_label_not_in_feature_registry():
    bad = {"future_return", "label", "threshold"}
    for d in FeatureRegistry.all():
        assert d.feature_name not in bad
        assert not (set(d.input_fields) & bad)


def test_D_missing_future_makes_unavailable_not_flat():
    recs = generate_labels("SPY", LABEL_DEFINITIONS["t1_up_flat_down"],
                           start="2026-09-01", end="2026-09-25")
    obs = {l.observation_time.date() for l in recs}
    assert pd.Timestamp("2026-09-25").date() not in obs  # 末尾无 T+1
