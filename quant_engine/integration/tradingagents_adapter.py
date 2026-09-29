# -*- coding: utf-8 -*-
"""TradingAgents Adapter：QuantState → quant_context 字符串（注入 AgentState）。"""
from __future__ import annotations

from datetime import datetime

from quant_engine.state.builders import build_quant_state
from quant_engine.state.models import QuantState

from .context import TradingAgentsQuantContext
from .renderer import render_quant_state, RENDERER_VERSION


def build_quant_context(symbol: str = "SPY",
                        as_of: datetime | None = None) -> TradingAgentsQuantContext:
    """构建 typed context（QuantState + rendered 文本）。"""
    state = build_quant_state(symbol, as_of)
    return TradingAgentsQuantContext(
        symbol=symbol, as_of=state.as_of, state=state,
        rendered=render_quant_state(state), renderer_version=RENDERER_VERSION,
    )


def to_quant_context_string(ctx: TradingAgentsQuantContext) -> str:
    """Typed context → 注入 AgentState.quant_context 的字符串。"""
    return ctx.rendered
