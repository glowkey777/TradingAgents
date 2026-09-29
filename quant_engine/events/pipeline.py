# -*- coding: utf-8 -*-
"""Event Study Pipeline：detect → dedup → forward → statistics。"""
from __future__ import annotations

from datetime import datetime

from .detector import detect_events
from .statistics import summarize
from .study import compute_forward_returns
from .validation import deduplicate, sample_size_gate


def run_event_study(symbol: str = "SPY", event_names: list[str] | None = None,
                    start: str = "2013-01-01", end: str = "2026-09-25",
                    horizons: list[str] | None = None,
                    as_of: datetime | None = None) -> dict:
    """端到端 Event Study。"""
    raw = detect_events(symbol, event_names, start, end, as_of)
    deduped = deduplicate(raw)
    forward = compute_forward_returns(deduped, horizons, as_of)
    stats = summarize(forward)
    gate = sample_size_gate(deduped)
    return {
        "raw_events": raw, "deduplicated_events": deduped,
        "forward_returns": forward, "statistics": stats,
        "sample_size_gate": gate,
        "event_count": len(deduped),
        "unique_events": len({e.event_name for e in deduped}),
    }
