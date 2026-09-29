# -*- coding: utf-8 -*-
"""Feature Registry：集中登记每个 feature 的定义，杜绝公式散落。"""
from __future__ import annotations

from .models import FeatureDefinition


class FeatureRegistry:
    _definitions: dict[str, FeatureDefinition] = {}
    _instances: dict[str, object] = {}

    @classmethod
    def register(cls, d: FeatureDefinition) -> None:
        cls._definitions[d.feature_name] = d

    @classmethod
    def register_instance(cls, name: str, inst: object) -> None:
        cls._instances[name] = inst

    @classmethod
    def instance(cls, name: str):
        if name not in cls._instances:
            raise KeyError(f"feature not registered: {name}")
        return cls._instances[name]

    @classmethod
    def instances(cls) -> dict[str, object]:
        return dict(cls._instances)

    @classmethod
    def get(cls, name: str) -> FeatureDefinition:
        if name not in cls._definitions:
            raise KeyError(f"feature not registered: {name}")
        return cls._definitions[name]

    @classmethod
    def all(cls) -> list[FeatureDefinition]:
        return list(cls._definitions.values())

    @classmethod
    def names(cls) -> list[str]:
        return sorted(cls._definitions)

    @classmethod
    def to_markdown(cls) -> str:
        header = ("| Feature | Formula | Input | Lookback | Frequency | PIT | Version |\n"
                  "| ------- | ------- | ----- | -------: | --------- | --- | ------- |")
        rows = []
        for d in cls.all():
            rows.append(f"| {d.feature_name} | {d.formula} | {','.join(d.input_fields)} "
                        f"| {d.lookback if d.lookback is not None else '-'} | {d.frequency} "
                        f"| YES | {d.feature_version} |")
        return header + "\n" + "\n".join(rows)
