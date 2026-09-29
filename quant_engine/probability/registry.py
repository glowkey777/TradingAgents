# -*- coding: utf-8 -*-
"""Probability Registry：登记概率模型定义。"""
from __future__ import annotations

from .models import ProbabilityDefinition


class ProbabilityRegistry:
    _definitions: dict[str, ProbabilityDefinition] = {}

    @classmethod
    def register(cls, d: ProbabilityDefinition) -> None:
        cls._definitions[d.probability_name] = d

    @classmethod
    def all(cls) -> list[ProbabilityDefinition]:
        return list(cls._definitions.values())

    @classmethod
    def get(cls, name: str) -> ProbabilityDefinition:
        return cls._definitions[name]
