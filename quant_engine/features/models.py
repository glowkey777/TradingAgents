# -*- coding: utf-8 -*-
"""Feature 强类型模型：FeatureDataPoint / FeatureDefinition / FeatureVersion。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

QualityFlag = Literal["OK", "MISSING_INPUT", "INSUFFICIENT_HISTORY",
                      "INVALID_INPUT", "PIT_BLOCKED"]


class FeatureDataPoint(BaseModel):
    """单个 feature 在某一 observation_time 的值。"""
    feature_name: str
    symbol: str
    observation_time: datetime       # feature 描述的时点
    available_at: datetime           # 该 feature 最早可用时点（继承源数据 PIT）
    as_of: datetime                  # 查询上下文（不是 observation_time）
    value: float | None = None
    frequency: str                   # daily / 15m / 30m / 1h / session
    unit: str | None = None
    source_data_version: str = ""
    feature_version: str = "v1"
    quality_flag: QualityFlag = "OK"

    def visible_at(self, as_of: datetime) -> bool:
        return self.available_at <= as_of


class FeatureDefinition(BaseModel):
    """Feature Registry 条目：完整、可追溯的定义。"""
    feature_name: str
    definition: str
    formula: str
    input_fields: list[str]
    frequency: str
    lookback: int | None = None
    availability_rule: str = "after current observation available"
    pit_rule: str = "inherited from source data"
    unit: str | None = None
    output_type: str = "float"
    feature_version: str = "v1"


class FeatureVersion(BaseModel):
    """feature_version 不可变标识。"""
    feature_name: str
    feature_version: str

    def key(self) -> str:
        return f"{self.feature_name}:{self.feature_version}"
