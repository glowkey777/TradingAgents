# -*- coding: utf-8 -*-
"""Probability Definitions：Baseline 模型 + 样本门阈值（versioned）。"""
from __future__ import annotations

from .models import ProbabilityDefinition
from .registry import ProbabilityRegistry

BASELINE_UNCONDITIONAL = ProbabilityDefinition(
    probability_name="baseline_unconditional",
    method="unconditional",
    inputs=["none (unconditional historical target distribution)"],
    horizon="T+1", lookback=None,
    minimum_sample_size=30, low_sample_size=100,
    smoothing_method="laplace", alpha=1.0, version="v1",
)

BASELINE_REGIME_CONDITIONAL = ProbabilityDefinition(
    probability_name="baseline_regime_conditional",
    method="regime_conditional",
    inputs=["P4 regime (trend/volatility/macro/event argmax)"],
    horizon="T+1",
    minimum_sample_size=30, low_sample_size=100,
    smoothing_method="laplace", alpha=1.0, version="v1",
)

BASELINE_EVENT_CONDITIONAL = ProbabilityDefinition(
    probability_name="baseline_event_conditional",
    method="event_conditional",
    inputs=["P3 events (weighted)"],
    horizon="T+1",
    minimum_sample_size=30, low_sample_size=100,
    smoothing_method="laplace", alpha=1.0, version="v1",
)

BASELINE_HIERARCHICAL = ProbabilityDefinition(
    probability_name="baseline_hierarchical",
    method="hierarchical",
    inputs=["P4 regime + P3 events + P2 features"],
    horizon="T+1",
    minimum_sample_size=30, low_sample_size=100,
    smoothing_method="laplace", alpha=1.0, version="v1",
)


def register() -> None:
    for d in (BASELINE_UNCONDITIONAL, BASELINE_REGIME_CONDITIONAL,
              BASELINE_EVENT_CONDITIONAL, BASELINE_HIERARCHICAL):
        ProbabilityRegistry.register(d)
