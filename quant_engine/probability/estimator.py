# -*- coding: utf-8 -*-
"""Estimator：条件分布 → P(label) + smoothing + sample gate + hierarchical fallback。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

import pandas as pd

from .models import ProbabilityDefinition, ProbabilityEstimate
from .calibration import IdentityCalibrator

# 主导状态 → 层级用的匹配键（Level 由粗到细）
LEVEL_DIMS = {
    1: ["trend", "volatility", "macro", "events"],
    2: ["trend", "volatility", "macro"],
    3: ["trend", "volatility"],
    4: ["trend"],
    5: [],
}


def _laplace(counts: dict[str, int], alpha: float) -> dict[str, float]:
    classes = ["UP", "FLAT", "DOWN"]
    n = sum(counts.values())
    return {c: (counts.get(c, 0) + alpha) / (n + len(classes) * alpha) for c in classes}


def _status(n: int, d: ProbabilityDefinition) -> str:
    if n < d.minimum_sample_size:
        return "INSUFFICIENT_SAMPLE"
    if n < d.low_sample_size:
        return "LOW_SAMPLE"
    return "VALID"


def _match_mask(history: pd.DataFrame, current: dict, dims: list[str]) -> pd.Series:
    mask = pd.Series(True, index=history.index)
    for dim in dims:
        if dim == "events":
            cur_events = set(current.get("events", []))
            mask &= history["events"].apply(
                lambda s: (s if isinstance(s, set) else set()) == cur_events)
        else:
            mask &= history[dim] == current.get(dim, "N/A")
    return mask


def estimate(history: pd.DataFrame, current: dict, definition: ProbabilityDefinition,
             horizon: str, observation_time: datetime, as_of: datetime,
             symbol: str = "SPY") -> ProbabilityEstimate:
    """按 method 选择条件逻辑；全程记录 evidence_level。"""
    label_col = "label_t1" if horizon == "T+1" else "label_t2"
    history = history.dropna(subset=[label_col])  # 无 label 的历史不可用

    method = definition.method
    used_level: int | None = None

    if method == "unconditional":
        matches = history
        used_level = 5
    elif method == "regime_conditional":
        matches = history[_match_mask(history, current,
                                      ["trend", "volatility", "macro", "events"])]
        used_level = 1
    elif method == "event_conditional":
        cur_events = set(current.get("events", []))
        if cur_events:
            matches = history[history["events"].apply(
                lambda s: bool((s if isinstance(s, set) else set()) & cur_events))]
            used_level = 1
        else:
            matches = history
            used_level = 5
    else:  # hierarchical：Level 1 → 5 fallback，样本不足逐级放宽
        for level in range(1, 6):
            matches = history[_match_mask(history, current, LEVEL_DIMS[level])]
            if len(matches) >= definition.minimum_sample_size:
                used_level = level
                break
        if used_level is None:
            used_level = 5
            matches = history

    counts = Counter(matches[label_col].dropna())
    p = _laplace(counts, definition.alpha)
    p_up, p_flat, p_down = IdentityCalibrator().transform(p["UP"], p["FLAT"], p["DOWN"])

    return ProbabilityEstimate(
        symbol=symbol, observation_time=observation_time, as_of=as_of,
        horizon=horizon, p_up=p_up, p_flat=p_flat, p_down=p_down,
        sample_size=int(len(matches)), evidence_level=used_level,
        method=definition.method, probability_version=definition.version,
        status=_status(len(matches), definition),
    )
