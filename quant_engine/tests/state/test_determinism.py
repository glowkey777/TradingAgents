# -*- coding: utf-8 -*-
"""Determinism 测试。"""
from quant_engine.state import build_quant_state, canonical_json


def test_deterministic_rebuild(state_2024):
    from datetime import datetime
    again = build_quant_state("SPY", datetime(2024, 6, 3, 23, 59, 59))
    assert canonical_json(state_2024) == canonical_json(again)
