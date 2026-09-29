# -*- coding: utf-8 -*-
"""Canonical Serialization：deterministic round-trip。"""
from __future__ import annotations

from .models import QuantState


def canonical_json(state: QuantState) -> str:
    """Pydantic 按字段定义顺序 + ISO-8601 datetime，deterministic。"""
    return state.model_dump_json()


def deserialize(data: str | bytes) -> QuantState:
    return QuantState.model_validate_json(data)


def round_trip(state: QuantState) -> bool:
    return deserialize(canonical_json(state)) == state
