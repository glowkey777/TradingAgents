# -*- coding: utf-8 -*-
"""Event Regime：normal_event / event_driven（复用 P3 Event Engine）。"""
from __future__ import annotations

from .models import RegimeDefinition, RegimeRule
from .registry import RegimeRegistry

# 事件严重度权重（versioned）
EVENT_WEIGHTS: dict[str, float] = {
    "large_down_day": 2.0, "large_up_day": 2.0,
    "large_gap_down": 1.5, "large_gap_up": 1.5,
    "vix_shock_up": 2.0, "vix_shock_down": 1.0,
    "realized_vol_shock": 2.0,
    "rsi_oversold": 1.0, "rsi_overbought": 1.0,
    "macd_bullish_cross": 1.0, "macd_bearish_cross": 1.0,
    "sma20_cross_sma50": 1.0, "price_cross_sma20": 1.0, "price_cross_sma50": 1.0,
    "us10y_shock": 1.5, "us5y_shock": 1.5, "dxy_shock": 1.0, "wti_shock": 1.5,
}

EVENT_FEATURES: list[str] = []  # 输入是 P3 事件，非 P2 feature

EVENT_RULES = [
    RegimeRule("event_weighted_sum", "event", "触发事件按 severity 权重累加"),
]


def score(events: list, sample_gate: dict[str, str]) -> dict[str, float]:
    """events: 当天触发的 EventRecord 列表；sample_gate: event_name -> SUFFICIENT/INSUFFICIENT_SAMPLE。"""
    event_score = 0.0
    for ev in events:
        if sample_gate.get(ev.event_name) == "INSUFFICIENT_SAMPLE":
            continue  # 小样本事件不得给正常证据权重
        event_score += EVENT_WEIGHTS.get(ev.event_name, 1.0)
    return {"normal_event": 1.0, "event_driven": event_score}


def register() -> None:
    for r in EVENT_RULES:
        RegimeRegistry.register_rule(r)
    RegimeRegistry.register_dimension(RegimeDefinition(
        dimension="event",
        definition="复用 P3 Event Engine，触发事件按 severity 加权，判定事件驱动程度",
        states=["normal_event", "event_driven"],
        input_features=EVENT_FEATURES,
        rule_names=[r.name for r in EVENT_RULES],
        version="v1",
    ))
