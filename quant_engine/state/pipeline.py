# -*- coding: utf-8 -*-
"""State Pipeline：build + validate。"""
from __future__ import annotations

from datetime import datetime

from .builders import build_quant_state
from .validation import validate_state


def run_state_pipeline(symbol: str = "SPY", as_of: datetime | None = None):
    state = build_quant_state(symbol, as_of)
    errors = validate_state(state)
    return {"state": state, "errors": errors, "valid": not errors}
