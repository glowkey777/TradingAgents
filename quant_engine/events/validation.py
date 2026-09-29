# -*- coding: utf-8 -*-
"""Event De-duplication + Sample-size gate。"""
from __future__ import annotations

import pandas as pd

from .models import EventRecord


def deduplicate(events: list[EventRecord]) -> list[EventRecord]:
    """按 event_name 分组，应用 deduplication_rule。

    first_trigger_only：连续触发（相邻 session）只保留第一个；
    cooldown：上次触发后 N sessions 内不再触发。
    """
    from .registry import EventRegistry

    out: list[EventRecord] = []
    for name in {e.event_name for e in events}:
        ev = EventRegistry.instance(name)
        grouped = sorted([e for e in events if e.event_name == name],
                         key=lambda e: e.observation_time)
        kept: list[EventRecord] = []
        last_kept: pd.Timestamp | None = None
        prev_trigger: pd.Timestamp | None = None
        for rec in grouped:
            ts = pd.Timestamp(rec.observation_time)
            if ev.deduplication_rule == "cooldown":
                if last_kept is not None and (ts - last_kept).days <= ev.cooldown:
                    continue
                kept.append(rec)
                last_kept = ts
            else:  # first_trigger_only
                if prev_trigger is not None and (ts - prev_trigger).days <= 5:
                    continue
                kept.append(rec)
                prev_trigger = ts
        out.extend(kept)
    return sorted(out, key=lambda e: e.observation_time)


def sample_size_gate(events: list[EventRecord], min_size: int = 30) -> dict[str, str]:
    """返回 event_name -> status（SUFFICIENT / INSUFFICIENT_SAMPLE）。"""
    from collections import Counter
    counts = Counter(e.event_name for e in events)
    return {name: ("SUFFICIENT" if n >= min_size else "INSUFFICIENT_SAMPLE")
            for name, n in counts.items()}
