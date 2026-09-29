# -*- coding: utf-8 -*-
"""TradingAgents Adapter：QuantState → 结构化 context（仅边界，不做 prompt/推理/决策）。"""
from __future__ import annotations

from .models import QuantState


def to_tradingagents_context(state: QuantState) -> dict:
    """QuantState → 下游可消费的结构化 dict。P6 只定义边界，不接 LLM 推理。"""
    return {
        "symbol": state.symbol,
        "as_of": state.as_of.isoformat(),
        "schema_version": state.schema_version,
        "market": {"close": state.market.close, "trading_date": state.market.trading_date.isoformat()},
        "regime": {
            "trend": state.regime.trend, "volatility": state.regime.volatility,
            "macro": state.regime.macro, "event": state.regime.event,
        },
        "probability": {
            "t1": _prob(state.probability.t1), "t2": _prob(state.probability.t2),
        },
        "active_events": [e.event_name for e in state.events.active_events],
        "data_quality": state.data_quality.status,
        "confidence": {"level": state.confidence.level, "score": state.confidence.score},
        "lineage": state.lineage.model_dump(),
    }


def _prob(est) -> dict | None:
    if est is None:
        return None
    return {"p_up": est.p_up, "p_flat": est.p_flat, "p_down": est.p_down,
            "sample_size": est.sample_size, "evidence_level": est.evidence_level,
            "status": est.status, "method": est.method}
