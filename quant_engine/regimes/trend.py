# -*- coding: utf-8 -*-
"""Trend Regime：bull_trend / bear_trend / range（互斥，sum=1）。"""
from __future__ import annotations

from .models import RegimeDefinition, RegimeRule
from .registry import RegimeRegistry

TREND_FEATURES = [
    "spy.distance_to_sma_20", "spy.distance_to_sma_50", "spy.distance_to_sma_200",
    "spy.sma_20", "spy.sma_50", "spy.sma_200", "spy.close_slope_20",
]

TREND_RULES = [
    # bull（+1 每条）
    RegimeRule("price_above_sma20", "trend", "spy.distance_to_sma_20 > 0"),
    RegimeRule("price_above_sma50", "trend", "spy.distance_to_sma_50 > 0"),
    RegimeRule("price_above_sma200", "trend", "spy.distance_to_sma_200 > 0"),
    RegimeRule("sma20_above_sma50", "trend", "spy.sma_20 > spy.sma_50"),
    RegimeRule("sma50_above_sma200", "trend", "spy.sma_50 > spy.sma_200"),
    # bear（+1 每条）
    RegimeRule("price_below_sma20", "trend", "spy.distance_to_sma_20 < 0"),
    RegimeRule("price_below_sma50", "trend", "spy.distance_to_sma_50 < 0"),
    RegimeRule("price_below_sma200", "trend", "spy.distance_to_sma_200 < 0"),
    RegimeRule("sma20_below_sma50", "trend", "spy.sma_20 < spy.sma_50"),
    RegimeRule("sma50_below_sma200", "trend", "spy.sma_50 < spy.sma_200"),
    # range（+1 每条）：不是 "not bull and not bear"，有明确依据
    RegimeRule("price_near_sma20", "trend", "abs(spy.distance_to_sma_20) < 0.01"),
    RegimeRule("sma20_sma50_proximity", "trend",
               "abs(spy.sma_20 - spy.sma_50) / spy.sma_50 < 0.005"),
    RegimeRule("low_trend_slope", "trend", "abs(spy.close_slope_20) < 0.10"),
]

def score(f: dict[str, float | None]) -> dict[str, float]:
    # 显式逐条判断（可读、可测）
    d20, d50, d200 = f.get("spy.distance_to_sma_20"), f.get("spy.distance_to_sma_50"), f.get("spy.distance_to_sma_200")
    s20, s50, s200 = f.get("spy.sma_20"), f.get("spy.sma_50"), f.get("spy.sma_200")
    slope = f.get("spy.close_slope_20")
    bull = bear = rng = 0.0

    if d20 is not None and d20 > 0:
        bull += 1
    if d50 is not None and d50 > 0:
        bull += 1
    if d200 is not None and d200 > 0:
        bull += 1
    if s20 is not None and s50 is not None and s20 > s50:
        bull += 1
    if s50 is not None and s200 is not None and s50 > s200:
        bull += 1

    if d20 is not None and d20 < 0:
        bear += 1
    if d50 is not None and d50 < 0:
        bear += 1
    if d200 is not None and d200 < 0:
        bear += 1
    if s20 is not None and s50 is not None and s20 < s50:
        bear += 1
    if s50 is not None and s200 is not None and s50 < s200:
        bear += 1

    if d20 is not None and abs(d20) < 0.01:
        rng += 1
    if s20 is not None and s50 is not None and abs(s20 - s50) / s50 < 0.005:
        rng += 1
    if slope is not None and abs(slope) < 0.10:
        rng += 1

    return {"bull_trend": bull, "bear_trend": bear, "range": rng}


def register() -> None:
    for r in TREND_RULES:
        RegimeRegistry.register_rule(r)
    RegimeRegistry.register_dimension(RegimeDefinition(
        dimension="trend",
        definition="价格相对 SMA20/50/200 的位置 + 均线排列 + 趋势斜率，判定趋势/震荡",
        states=["bull_trend", "bear_trend", "range"],
        input_features=TREND_FEATURES,
        rule_names=[r.name for r in TREND_RULES],
        version="v1",
    ))
