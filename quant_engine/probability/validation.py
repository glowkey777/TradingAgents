# -*- coding: utf-8 -*-
"""Probability Validation：leakage 检查。"""
from __future__ import annotations

from .models import ProbabilityEstimate


def probability_valid(est: ProbabilityEstimate) -> bool:
    return (0 <= est.p_up <= 1 and 0 <= est.p_flat <= 1 and 0 <= est.p_down <= 1
            and abs(est.p_up + est.p_flat + est.p_down - 1) < 1e-6)


def no_label_in_inputs(definition) -> bool:
    """label/future_return 不得进入概率输入。"""
    for s in definition.inputs:
        if "label" in s or "future" in s:
            return False
    return True


def no_future_leak(est: ProbabilityEstimate) -> bool:
    """as_of 必须 >= observation_time（估计用截至 T 信息）。"""
    return est.observation_time <= est.as_of
