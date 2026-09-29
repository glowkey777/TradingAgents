# -*- coding: utf-8 -*-
"""Macro Regime：normal_macro / macro_shock。"""
from __future__ import annotations

from .models import RegimeDefinition, RegimeRule
from .registry import RegimeRegistry

MACRO_FEATURES = ["macro.us10y_change_1d", "macro.us5y_change_1d",
                  "macro.dxy_change_1d", "macro.wti_change_1d", "macro.us10y_us5y_spread"]

MACRO_RULES = [
    RegimeRule("us10y_shock", "macro", "abs(macro.us10y_change_1d) > 0.05"),
    RegimeRule("us5y_shock", "macro", "abs(macro.us5y_change_1d) > 0.05"),
    RegimeRule("dxy_shock", "macro", "abs(macro.dxy_change_1d) > 0.01"),
    RegimeRule("wti_shock", "macro", "abs(macro.wti_change_1d) > 0.05"),
]


def score(f: dict[str, float | None]) -> dict[str, float]:
    shock = 0.0
    u10 = f.get("macro.us10y_change_1d")
    u5 = f.get("macro.us5y_change_1d")
    dxy = f.get("macro.dxy_change_1d")
    wti = f.get("macro.wti_change_1d")
    if u10 is not None and abs(u10) > 0.05:
        shock += 1
    if u5 is not None and abs(u5) > 0.05:
        shock += 1
    if dxy is not None and abs(dxy) > 0.01:
        shock += 1
    if wti is not None and abs(wti) > 0.05:
        shock += 1
    return {"normal_macro": 1.0, "macro_shock": shock}


def register() -> None:
    for r in MACRO_RULES:
        RegimeRegistry.register_rule(r)
    RegimeRegistry.register_dimension(RegimeDefinition(
        dimension="macro",
        definition="美债/美元/原油单日异常变动，判定宏观是否处于 shock 状态",
        states=["normal_macro", "macro_shock"],
        input_features=MACRO_FEATURES,
        rule_names=[r.name for r in MACRO_RULES],
        version="v1",
    ))
