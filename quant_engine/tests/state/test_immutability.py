# -*- coding: utf-8 -*-
"""Immutability 测试。"""
import pytest


def test_quantstate_frozen(state_2024):
    with pytest.raises(Exception):
        state_2024.symbol = "QQQ"
    with pytest.raises(Exception):
        state_2024.as_of = None


def test_snapshot_frozen(state_2024):
    with pytest.raises(Exception):
        state_2024.market.close = 999.0
