# -*- coding: utf-8 -*-
"""Regime 模型：RegimeRule / RegimeDefinition / RegimeState / RegimeProbability。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

PROBABILITY_TYPE = "RULE_BASED_REGIME_SCORE"


class RegimeProbability(BaseModel):
    """单个状态的概率（normalized regime score，非 ML 概率）。"""
    regime_name: str
    probability: float | None = None      # None = 该状态无数据/不可用
    confidence: float | None = None
    status: str = "OK"                    # OK | NOT_AVAILABLE | INSUFFICIENT_DATA


class RegimeRule(BaseModel):
    """一条可版本化评分规则。"""
    name: str
    dimension: str
    condition: str
    weight: float = 1.0
    version: str = "v1"

    def __init__(self, name: str, dimension: str, condition: str,
                 weight: float = 1.0, version: str = "v1", **kw):
        super().__init__(name=name, dimension=dimension, condition=condition,
                         weight=weight, version=version)


class RegimeDefinition(BaseModel):
    """一个 Regime 维度的定义（trend/volatility/macro/event）。"""
    dimension: str
    definition: str
    states: list[str]                     # 互斥状态列表
    input_features: list[str]
    rule_names: list[str]
    version: str = "v1"
    probability_type: str = PROBABILITY_TYPE


class RegimeState(BaseModel):
    """某 observation_time 的完整多维 Regime 状态。"""
    symbol: str
    observation_time: datetime
    as_of: datetime

    trend: dict[str, float] = {}          # {bull_trend, bear_trend, range}
    volatility: dict[str, float] = {}     # {low_volatility, normal_volatility, high_volatility}
    macro: dict[str, float] = {}          # {normal_macro, macro_shock}
    event: dict[str, float] = {}          # {normal_event, event_driven}

    confidence: dict[str, float] = {}     # 每维 confidence（data completeness）
    status: dict[str, str] = {}           # 每维 status（OK/NOT_AVAILABLE/INSUFFICIENT_DATA）

    regime_version: str = "v1"
    source_feature_versions: list[str] = ["p2_v1"]
    source_event_versions: list[str] = ["p3_v1"]
    probability_type: str = PROBABILITY_TYPE

    def overall_status(self) -> str:
        if all(v == "NOT_AVAILABLE" for v in self.status.values()):
            return "NOT_AVAILABLE"
        if any(v == "NOT_AVAILABLE" or v == "INSUFFICIENT_DATA" for v in self.status.values()):
            return "PARTIAL"
        return "OK"
