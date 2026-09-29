# -*- coding: utf-8 -*-
"""Regime Engine：组装四维 scorer → RegimeState。"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache

import pandas as pd

from quant_engine.events import detect_events, EventRegistry
from quant_engine.events.validation import sample_size_gate, deduplicate

from . import trend, volatility, macro, event
from .inputs import collect_features, FEATURE_NAMES
from .models import RegimeState
from .scorers import normalize, data_completeness

_DEFAULT_AS_OF = datetime(2100, 1, 1)


@lru_cache(maxsize=1)
def _global_sample_gate() -> tuple:
    """全历史去重后的 sample gate（样本量必须基于全历史，不是窗口内）。"""
    raw = detect_events("SPY", None, "2013-01-01", "2026-09-25")
    return tuple(sorted(sample_size_gate(deduplicate(raw)).items()))


def _dimension_status(raw: dict[str, float], present_count: int) -> str:
    if present_count == 0:
        return "NOT_AVAILABLE"
    if sum(raw.values()) <= 0:
        return "INSUFFICIENT_DATA"
    return "OK"


def compute_regime(symbol: str, observation_time, as_of: datetime | None = None) -> RegimeState:
    as_of = as_of or _DEFAULT_AS_OF
    ts = pd.Timestamp(observation_time)
    f = collect_features(symbol, ts, as_of)

    day = ts.normalize()
    start = str((day - timedelta(days=10)).date())  # 窗口含 lookback，避免 return/gap 漏检
    raw_events = detect_events(symbol, None, start, str(day.date()), as_of)
    gate = dict(_global_sample_gate())  # 全历史样本门，非窗口内
    day_events = [e for e in raw_events if pd.Timestamp(e.observation_time).date() == day.date()]

    trend_raw = trend.score(f)
    vol_raw = volatility.score(f)
    macro_raw = macro.score(f)
    event_raw = event.score(day_events, gate)

    trend_prob = normalize(trend_raw)
    vol_prob = normalize(vol_raw)
    macro_prob = normalize(macro_raw)
    event_prob = normalize(event_raw)

    trend_present = sum(1 for k in trend.TREND_FEATURES if f.get(k) is not None)
    vol_present = sum(1 for k in volatility.VOL_FEATURES if f.get(k) is not None)
    macro_present = sum(1 for k in macro.MACRO_FEATURES if f.get(k) is not None)

    status = {
        "trend": _dimension_status(trend_raw, trend_present),
        "volatility": _dimension_status(vol_raw, vol_present),
        "macro": _dimension_status(macro_raw, macro_present),
        "event": "OK",  # event 维度有 baseline normal_event=1.0，永有值
    }
    confidence = {
        "trend": data_completeness({k: f.get(k) for k in trend.TREND_FEATURES}),
        "volatility": data_completeness({k: f.get(k) for k in volatility.VOL_FEATURES}),
        "macro": data_completeness({k: f.get(k) for k in macro.MACRO_FEATURES}),
        "event": 1.0,
    }

    return RegimeState(
        symbol=symbol, observation_time=ts.to_pydatetime(), as_of=as_of,
        trend=trend_prob, volatility=vol_prob, macro=macro_prob, event=event_prob,
        confidence=confidence, status=status,
        regime_version="v1",
        source_feature_versions=["p2_v1"], source_event_versions=["p3_v1"],
    )
