# -*- coding: utf-8 -*-
"""Label 模型：LabelDefinition / LabelRecord。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LabelDefinition(BaseModel):
    label_name: str
    horizon: str                      # "T+1" / "T+2"
    threshold_method: str             # "realized_vol_daily"
    threshold_multiplier: float       # k（版本化参数）
    label_version: str = "v1"


class LabelRecord(BaseModel):
    """监督学习目标。future_return 用未来数据，绝不进 Feature/Event。"""
    symbol: str
    observation_time: datetime
    horizon: str
    future_return: float
    threshold: float
    label: str                        # UP / FLAT / DOWN
    label_version: str = "v1"
    source_data_version: str = ""
    feature_cutoff: str = ""          # 阈值用的 feature 截止（无泄漏说明）
