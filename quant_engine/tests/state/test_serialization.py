# -*- coding: utf-8 -*-
"""Serialization 测试：round-trip。"""
from quant_engine.state import canonical_json, deserialize, round_trip


def test_json_round_trip(state_2024):
    j = canonical_json(state_2024)
    assert deserialize(j) == state_2024
    assert round_trip(state_2024)


def test_json_is_valid_json(state_2024):
    import json
    json.loads(canonical_json(state_2024))
