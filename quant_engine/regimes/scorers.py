# -*- coding: utf-8 -*-
"""Rule-based Scoring 框架：累加权重 → normalize。"""
from __future__ import annotations


def normalize(scores: dict[str, float]) -> dict[str, float]:
    """把规则得分归一化为概率分布（sum=1）。全 0 返回空 dict（无数据）。"""
    total = sum(v for v in scores.values() if v is not None)
    if total <= 0:
        return {}
    return {k: (v or 0.0) / total for k, v in scores.items()}


def data_completeness(values: dict[str, float | None]) -> float:
    """confidence 来源之一：有多少输入 feature 有值。"""
    if not values:
        return 0.0
    n = sum(1 for v in values.values() if v is not None)
    return n / len(values)
