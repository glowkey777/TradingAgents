# -*- coding: utf-8 -*-
"""QuantState 模型测试。"""
from quant_engine.state.models import QuantState, SCHEMA_VERSION, STATE_VERSION


def test_schema_versions_distinct(state_2024):
    assert state_2024.schema_version == SCHEMA_VERSION == "quant-state-schema-v1"
    assert state_2024.state_version == STATE_VERSION == "quant-state-v1.0.0"
    assert state_2024.schema_version != state_2024.state_version


def test_quantstate_is_typed(state_2024):
    assert isinstance(state_2024, QuantState)
    assert state_2024.symbol == "SPY"
    assert state_2024.regime is not None
    assert state_2024.probability is not None
