# -*- coding: utf-8 -*-
"""TradingThesis 强类型契约（P7 STEP 5）。

三个锁死概念：
1. confidence ≠ p_up（thesis confidence 是 Agent 对证据一致性的自评，不是概率）
2. LLM 不得创造 QuantState 中不存在的数据（NOT_AVAILABLE 就写 NOT_AVAILABLE）
3. Thesis 必须能通过 quant_state_version + source_lineage 追溯回 P6/P1-P5
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_engine.state.models import StateLineage

THESIS_SCHEMA_VERSION = "thesis-schema-v1"
TOLERANCE = 1e-6


class DirectionalBias(str, Enum):
    """Agent 的研究结论（不是统计概率）。"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class EvidenceReference(BaseModel):
    """一条可追溯证据：指向 feature/event/regime/probability/risk/market。"""
    model_config = ConfigDict(frozen=True)
    source_type: Literal["feature", "event", "regime", "probability", "risk", "market"]
    source_id: str
    value: str | None = None
    statement: str = ""                  # Agent 对该证据的解读


class ThesisConfidence(BaseModel):
    """Agent 对自身研究结论的置信度（≠ p_up）。"""
    model_config = ConfigDict(frozen=True)
    score: float = Field(ge=0.0, le=1.0)
    level: Literal["high", "medium", "low"]
    method: str = "agent_self_assessment"
    version: str = "v1"


class ProbabilityReference(BaseModel):
    """引用 P5 概率（不重新计算、不修改）。"""
    model_config = ConfigDict(frozen=True)
    horizon: str                         # T+1 / T+2
    p_up: float
    p_flat: float
    p_down: float


class ModelProvenance(BaseModel):
    """LLM provenance（可追溯，不复用 TradingAgents 已有 metadata 就重复实现）。"""
    model_config = ConfigDict(frozen=True)
    provider: str
    model: str
    temperature: float | None = None
    prompt_version: str
    agent_version: str
    run_id: str


class TradingThesis(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = THESIS_SCHEMA_VERSION
    thesis_version: str = "v1"

    thesis_id: str
    symbol: str
    as_of: datetime
    horizon: str                         # T+1 / T+2

    directional_bias: DirectionalBias
    confidence: ThesisConfidence

    probability_reference: ProbabilityReference

    supporting_evidence: list[EvidenceReference] = []
    contradicting_evidence: list[EvidenceReference] = []
    invalidation_conditions: list[str] = []

    regime_snapshot: dict[str, dict[str, float]]   # trend/volatility/macro/event（引用 P4）
    thesis_summary: str = ""                       # LLM 生成（STEP 5.7 才填）

    quant_state_version: str                       # 追溯回 P6
    renderer_version: str
    source_lineage: StateLineage                   # 追溯回 P1-P5

    model_provenance: ModelProvenance
    created_at: datetime

    @model_validator(mode="after")
    def _check_valid(self):
        pr = self.probability_reference
        s = pr.p_up + pr.p_flat + pr.p_down
        if abs(s - 1.0) > TOLERANCE:
            raise ValueError(f"probability_reference 和={s} != 1")
        for name in ("p_up", "p_flat", "p_down"):
            v = getattr(pr, name)
            if not (-TOLERANCE <= v <= 1 + TOLERANCE):
                raise ValueError(f"{name}={v} 越界 [0,1]")
        return self
