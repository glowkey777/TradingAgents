# -*- coding: utf-8 -*-
"""Event 基类：显式定义 + 自动注册 + PIT 继承。"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from .models import EventDefinition
from .registry import EventRegistry


class Event(ABC):
    """Event 基类。detect(df) 输入 feature 值 wide 表（columns=feature 名），输出 bool 序列。"""

    name: str = ""
    definition: str = ""
    input_features: list[str] = []
    threshold: float | None = None
    frequency: str = "daily"
    event_version: str = "v1"
    deduplication_rule: str = "first_trigger_only"
    cooldown: int = 5
    minimum_sample_size: int = 30

    @abstractmethod
    def detect(self, df: pd.DataFrame) -> pd.Series:
        """返回 bool Series（True=事件发生）。df 是 feature 值 wide 表。"""

    def to_definition(self) -> EventDefinition:
        return EventDefinition(
            event_name=self.name, definition=self.definition,
            input_features=self.input_features, threshold=self.threshold,
            frequency=self.frequency, event_version=self.event_version,
            deduplication_rule=self.deduplication_rule, cooldown=self.cooldown,
            minimum_sample_size=self.minimum_sample_size,
        )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "name", "") and "detect" in cls.__dict__:
            inst = cls()
            EventRegistry.register(inst.to_definition())
            EventRegistry.register_instance(cls.name, inst)
