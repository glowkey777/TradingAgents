# -*- coding: utf-8 -*-
"""Event Registry：集中登记每个事件定义。"""
from __future__ import annotations

from .models import EventDefinition


class EventRegistry:
    _definitions: dict[str, EventDefinition] = {}
    _instances: dict[str, object] = {}

    @classmethod
    def register(cls, d: EventDefinition) -> None:
        cls._definitions[d.event_name] = d

    @classmethod
    def register_instance(cls, name: str, inst: object) -> None:
        cls._instances[name] = inst

    @classmethod
    def instance(cls, name: str):
        return cls._instances[name]

    @classmethod
    def instances(cls) -> dict[str, object]:
        return dict(cls._instances)

    @classmethod
    def all(cls) -> list[EventDefinition]:
        return list(cls._definitions.values())

    @classmethod
    def names(cls) -> list[str]:
        return sorted(cls._definitions)
