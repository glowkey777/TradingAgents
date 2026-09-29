# -*- coding: utf-8 -*-
"""Regime Validation：missing data 语义 + leakage 检查。"""
from __future__ import annotations

from .models import RegimeState


def no_future_leak(state: RegimeState) -> bool:
    """as_of 早于 observation 时，状态应 NOT_AVAILABLE（看不到当日收盘后 feature）。"""
    return state.observation_time <= state.as_of


def no_label_contamination(state: RegimeState) -> bool:
    """Regime 输入不含 label/future_return（结构性保证，由 inputs/engine 决定）。"""
    for d in (state.trend, state.volatility, state.macro, state.event):
        for k in d:
            if "label" in k or "future" in k or "return" in k:
                return False
    return True
