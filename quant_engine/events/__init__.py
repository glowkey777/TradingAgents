# -*- coding: utf-8 -*-
"""Event Study 模块（P3-A）。"""
from .base import Event
from .models import EventDefinition, EventRecord
from .registry import EventRegistry
from .detector import detect_events
from .study import compute_forward_returns, HORIZONS
from .statistics import summarize
from .validation import deduplicate, sample_size_gate
from .pipeline import run_event_study

# 导入事件定义，触发注册
from . import definitions as _definitions  # noqa: F401

__all__ = [
    "Event", "EventDefinition", "EventRecord", "EventRegistry",
    "detect_events", "compute_forward_returns", "summarize",
    "deduplicate", "sample_size_gate", "run_event_study", "HORIZONS",
]
