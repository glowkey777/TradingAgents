# -*- coding: utf-8 -*-
"""TradingAgentsQuantContext：typed context（引用 QuantState，不复制）。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from quant_engine.state.models import QuantState


class TradingAgentsQuantContext(BaseModel):
    """QuantState 的 typed 包装，供 adapter 注入 TradingAgents。

    state = 引用（source of truth），rendered = deterministic 文本（presentation）。
    """
    symbol: str
    as_of: datetime
    state: QuantState
    rendered: str
    renderer_version: str
