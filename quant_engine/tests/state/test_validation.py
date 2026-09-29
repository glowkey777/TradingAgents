# -*- coding: utf-8 -*-
"""State Validation 测试。"""
from quant_engine.state import validate_state


def test_validation_passes_clean(state_2024):
    assert validate_state(state_2024) == []


def test_validation_passes_crash(state_crash):
    assert validate_state(state_crash) == []
