# -*- coding: utf-8 -*-
"""Event Detector：从 P2 feature 值检测事件（PIT-safe）。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from quant_engine.features.pipeline import build_features

from .models import EventRecord
from .registry import EventRegistry


def _feature_wide(symbol: str, feature_names: list[str], start: str, end: str,
                  as_of: datetime | None) -> pd.DataFrame:
    pts = build_features(symbol, "daily", start=start, end=end,
                         as_of=as_of, feature_names=feature_names)
    rows = [p.model_dump() for p in pts if p.quality_flag == "OK"]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    wide = df.pivot_table(index="observation_time", columns="feature_name",
                          values="value", aggfunc="last")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def detect_events(symbol: str, event_names: list[str] | None = None,
                  start: str = "2013-01-01", end: str = "2026-09-25",
                  as_of: datetime | None = None) -> list[EventRecord]:
    """检测事件。事件只使用 available_at <= as_of 的 feature 数据。"""
    names = event_names or EventRegistry.names()
    needed = set()
    for n in names:
        needed.update(EventRegistry.instance(n).input_features)
    wide = _feature_wide(symbol, list(needed), start, end, as_of)
    if wide.empty:
        return []

    records: list[EventRecord] = []
    for n in names:
        ev = EventRegistry.instance(n)
        try:
            mask = ev.detect(wide)
        except KeyError:
            continue  # 输入 feature 缺失（如 15m 边界前）
        for ts, hit in mask.items():
            if not hit or pd.isna(hit):
                continue
            val = None
            if ev.input_features and ev.input_features[0] in wide.columns:
                v = wide.loc[ts, ev.input_features[0]]
                val = float(v) if not pd.isna(v) else None
            records.append(EventRecord(
                event_name=n, symbol=symbol,
                observation_time=ts.to_pydatetime(), event_time=ts.to_pydatetime(),
                available_at=(ts.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)).to_pydatetime(),
                as_of=as_of or datetime(2100, 1, 1),
                event_value=val, threshold=ev.threshold,
                event_version=ev.event_version, source_feature_versions="p2_v1"))
    return records
