# -*- coding: utf-8 -*-
"""Volatility Regime：low / normal / high（互斥，sum=1）。"""
from __future__ import annotations

from .models import RegimeDefinition, RegimeRule
from .registry import RegimeRegistry

VOL_FEATURES = ["vix_level", "macro.vix_change_1d", "macro.vix_percentile_60",
                "spy.realized_vol_20", "spy.atr_14"]

VOL_RULES = [
    RegimeRule("vix_low", "volatility", "vix_level < 15"),
    RegimeRule("vix_normal", "volatility", "15 <= vix_level <= 25"),
    RegimeRule("vix_high", "volatility", "vix_level > 25"),
    RegimeRule("rv_low", "volatility", "spy.realized_vol_20 < 0.10"),
    RegimeRule("rv_normal", "volatility", "0.10 <= spy.realized_vol_20 <= 0.20"),
    RegimeRule("rv_high", "volatility", "spy.realized_vol_20 > 0.20"),
    RegimeRule("vix_shock_up", "volatility", "macro.vix_change_1d > 0.10"),
    RegimeRule("vix_percentile_high", "volatility", "macro.vix_percentile_60 > 0.8"),
    RegimeRule("vix_percentile_low", "volatility", "macro.vix_percentile_60 < 0.2"),
]


def score(f: dict[str, float | None]) -> dict[str, float]:
    low = normal = high = 0.0
    vix = f.get("vix_level")
    rv = f.get("spy.realized_vol_20")
    vc = f.get("macro.vix_change_1d")
    vp = f.get("macro.vix_percentile_60")

    if vix is not None:
        if vix < 15:
            low += 1
        elif vix <= 25:
            normal += 1
        else:
            high += 1
    if rv is not None:
        if rv < 0.10:
            low += 1
        elif rv <= 0.20:
            normal += 1
        else:
            high += 1
    if vc is not None and vc > 0.10:
        high += 1
    if vp is not None:
        if vp > 0.8:
            high += 1
        elif vp < 0.2:
            low += 1

    return {"low_volatility": low, "normal_volatility": normal, "high_volatility": high}


def register() -> None:
    for r in VOL_RULES:
        RegimeRegistry.register_rule(r)
    RegimeRegistry.register_dimension(RegimeDefinition(
        dimension="volatility",
        definition="VIX 水平 + realized vol + VIX 变化 + VIX 分位，判定低/正常/高波动",
        states=["low_volatility", "normal_volatility", "high_volatility"],
        input_features=VOL_FEATURES,
        rule_names=[r.name for r in VOL_RULES],
        version="v1",
    ))
