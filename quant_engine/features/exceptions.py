# -*- coding: utf-8 -*-
"""Feature Engine 异常。"""
from __future__ import annotations


class FeatureError(Exception):
    """Feature 计算错误基类。"""


class InsufficientHistoryError(FeatureError):
    """历史数据不足以计算 feature（lookback 未满足）。"""


class InvalidInputError(FeatureError):
    """输入数据非法（字段缺失/类型错误）。"""


class PitBlockedError(FeatureError):
    """PIT 语义下该 feature 在 as_of 时点不可计算。"""


class MissingInputError(FeatureError):
    """输入字段在 as_of 时点不可得。"""
