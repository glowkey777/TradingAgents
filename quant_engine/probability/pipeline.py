# -*- coding: utf-8 -*-
"""Probability Pipeline：walk-forward 估计 + temporal split 评价。"""
from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

from .evidence import build_history_table
from .estimator import estimate
from .definitions import register, BASELINE_UNCONDITIONAL, BASELINE_REGIME_CONDITIONAL
from .registry import ProbabilityRegistry

# temporal split（按时间顺序，禁止 random split）
TEMPORAL_SPLIT = {
    "train": ("2013-01-01", "2020-12-31"),
    "validation": ("2021-01-01", "2023-12-31"),
    "test": ("2024-01-01", "2026-09-25"),
}


def run_walk_forward(history: pd.DataFrame, definition, horizon: str,
                     start: str, end: str, symbol: str = "SPY",
                     as_of: datetime | None = None) -> list:
    """对 [start, end] 每个交易日，只用「截至当日」的历史（PIT）估计概率。"""
    estimates = []
    for date in history.index:
        if date < pd.Timestamp(start) or date > pd.Timestamp(end):
            continue
        past = history[history.index < date]
        if past.empty:
            continue
        cur = history.loc[date]
        current = {
            "trend": cur["trend"], "volatility": cur["volatility"],
            "macro": cur["macro"], "events": cur["events"],
        }
        est = estimate(past, current, definition, horizon,
                       date.to_pydatetime(), as_of or datetime(2100, 1, 1), symbol)
        estimates.append(est)
    return estimates


def _log_loss(estimates, history, horizon) -> float | None:
    label_col = "label_t1" if horizon == "T+1" else "label_t2"
    total, n = 0.0, 0
    for est in estimates:
        actual = history.loc[pd.Timestamp(est.observation_time), label_col]
        if pd.isna(actual):
            continue
        p = {"UP": est.p_up, "FLAT": est.p_flat, "DOWN": est.p_down}[actual]
        total += -math.log(max(p, 1e-12))
        n += 1
    return total / n if n else None


def _brier(estimates, history, horizon) -> float | None:
    label_col = "label_t1" if horizon == "T+1" else "label_t2"
    total, n = 0.0, 0
    for est in estimates:
        actual = history.loc[pd.Timestamp(est.observation_time), label_col]
        if pd.isna(actual):
            continue
        one_hot = {"UP": [1, 0, 0], "FLAT": [0, 1, 0], "DOWN": [0, 0, 1]}[actual]
        pred = [est.p_up, est.p_flat, est.p_down]
        total += sum((p - a) ** 2 for p, a in zip(pred, one_hot))
        n += 1
    return total / n if n else None


def evaluate(history, definition, horizon, split: str = "test") -> dict:
    start, end = TEMPORAL_SPLIT[split]
    ests = run_walk_forward(history, definition, horizon, start, end)
    return {
        "split": split, "horizon": horizon, "method": definition.probability_name,
        "n": len(ests),
        "log_loss": _log_loss(ests, history, horizon),
        "brier": _brier(ests, history, horizon),
    }


def run_probability(horizon: str = "T+1") -> dict:
    """端到端：构建历史表 → 四个 baseline 在 test 期评价。"""
    register()
    history = build_history_table("2013-01-01", "2026-09-25")
    results = {}
    for d in (BASELINE_UNCONDITIONAL, BASELINE_REGIME_CONDITIONAL, BASELINE_HIERARCHICAL):
        results[d.probability_name] = evaluate(history, d, horizon, "test")
    return {"history": history, "results": results}
