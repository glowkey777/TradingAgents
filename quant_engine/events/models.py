# -*- coding: utf-8 -*-
"""Event 模型：EventDefinition / EventRecord。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventDefinition(BaseModel):
    event_name: str
    definition: str
    input_features: list[str]
    threshold: float | None = None
    frequency: str = "daily"
    event_version: str = "v1"
    deduplication_rule: str = "first_trigger_only"   # first_trigger_only | cooldown
    cooldown: int = 5                                 # sessions
    minimum_sample_size: int = 30


class EventRecord(BaseModel):
    """事件在某 observation_time 触发。event_time ≠ available_at。"""
    event_name: str
    symbol: str
    observation_time: datetime
    event_time: datetime
    available_at: datetime
    as_of: datetime
    event_value: float | None = None      # 触发时 feature 值
    threshold: float | None = None
    event_version: str = "v1"
    source_feature_versions: str = ""

    def visible_at(self, as_of: datetime) -> bool:
        return self.available_at <= as_of
