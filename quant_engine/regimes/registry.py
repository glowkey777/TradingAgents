# -*- coding: utf-8 -*-
"""Regime Registry：登记维度定义 + 评分规则。"""
from __future__ import annotations

from .models import RegimeDefinition, RegimeRule


class RegimeRegistry:
    _dimensions: dict[str, RegimeDefinition] = {}
    _rules: dict[str, RegimeRule] = {}

    @classmethod
    def register_dimension(cls, d: RegimeDefinition) -> None:
        cls._dimensions[d.dimension] = d

    @classmethod
    def register_rule(cls, r: RegimeRule) -> None:
        cls._rules[r.name] = r

    @classmethod
    def dimensions(cls) -> list[RegimeDefinition]:
        return list(cls._dimensions.values())

    @classmethod
    def rules(cls) -> list[RegimeRule]:
        return list(cls._rules.values())

    @classmethod
    def rules_for(cls, dimension: str) -> list[RegimeRule]:
        return [r for r in cls._rules.values() if r.dimension == dimension]
