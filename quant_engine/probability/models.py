# -*- coding: utf-8 -*-
"""Probability 模型：ProbabilityEstimate / ProbabilityDefinition。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

TOLERANCE = 1e-6


class ProbabilityEstimate(BaseModel):
    """SPY T+1/T+2 方向概率估计（UP/FLAT/DOWN，sum=1）。"""
    symbol: str
    observation_time: datetime
    as_of: datetime

    horizon: str                          # "T+1" / "T+2"

    p_up: float
    p_flat: float
    p_down: float

    sample_size: int
    evidence_level: int                   # 1-5，实际使用的证据层级

    method: str
    probability_version: str

    feature_version: str = "p2_v1"
    event_version: str = "p3_v1"
    regime_version: str = "p4_v1"
    label_version: str = "p3_v1"

    status: str = "VALID"                 # VALID / LOW_SAMPLE / INSUFFICIENT_SAMPLE

    @model_validator(mode="after")
    def _check_valid(self):
        for name in ("p_up", "p_flat", "p_down"):
            v = getattr(self, name)
            if not (-TOLERANCE <= v <= 1 + TOLERANCE):
                raise ValueError(f"{name}={v} 越界 [0,1]")
        s = self.p_up + self.p_flat + self.p_down
        if abs(s - 1.0) > TOLERANCE:
            raise ValueError(f"概率和={s}，必须 sum=1")
        return self


class ProbabilityDefinition(BaseModel):
    """一个可版本化概率模型的完整定义。"""
    probability_name: str
    method: str                           # unconditional / regime_conditional / event_conditional / hierarchical
    inputs: list[str]                     # 输入（P2 features / P3 events / P4 regime）
    horizon: str
    lookback: int | None = None
    sample_filter: str = ""
    similarity_definition: str = "exact_match"
    minimum_sample_size: int = 30
    low_sample_size: int = 100
    smoothing_method: str = "laplace"
    alpha: float = 1.0                    # Laplace smoothing 参数，版本化
    version: str = "v1"
