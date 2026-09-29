# -*- coding: utf-8 -*-
"""Builder 测试。"""
from quant_engine.state import build_quant_state


def test_build_has_all_layers(state_2024):
    s = state_2024
    for layer in ("market", "features", "events", "evidence", "regime",
                  "probability", "risk", "data_quality", "confidence", "lineage"):
        assert getattr(s, layer) is not None, f"{layer} 缺失"


def test_market_close_not_none(state_2024):
    assert state_2024.market.close is not None
    assert state_2024.market.close > 0


def test_features_nonempty(state_2024):
    assert len(state_2024.features.available_features) > 0
