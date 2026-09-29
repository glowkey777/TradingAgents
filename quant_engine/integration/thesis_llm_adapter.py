# -*- coding: utf-8 -*-
"""Thesis LLM Adapter：LLM 结构化输出 → CandidateThesis → 系统注入 → TradingThesis。

安全边界：LLM 只能生成 6 个字段（directional_bias/thesis_summary/confidence/
supporting/contradicting/invalidation）。系统字段（probability/lineage/version/
provenance/as_of/regime）由 assemble_thesis 注入，LLM 结构上无法覆盖。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from quant_engine.state.models import QuantState

from .renderer import RENDERER_VERSION
from .thesis import (
    TradingThesis, DirectionalBias, ThesisConfidence, ProbabilityReference,
    ModelProvenance, EvidenceReference,
)


class CandidateThesis(BaseModel):
    """LLM 能生成的字段（不含任何系统字段）。"""
    directional_bias: DirectionalBias
    thesis_summary: str = ""
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: Literal["high", "medium", "low"] = "low"
    supporting_evidence: list[EvidenceReference] = []
    contradicting_evidence: list[EvidenceReference] = []
    invalidation_conditions: list[str] = []


def parse_candidate(raw: str | bytes) -> CandidateThesis:
    """解析 LLM 结构化输出；malformed → ValidationError（REJECT）。"""
    return CandidateThesis.model_validate_json(raw)


def assemble_thesis(
    candidate: CandidateThesis,
    state: QuantState,
    horizon: str,
    run_id: str,
    provider: str,
    model: str,
    prompt_version: str,
    agent_version: str,
    temperature: float | None = None,
) -> TradingThesis:
    """系统注入 provenance/probability/lineage/version/as_of/regime。

    LLM 提供的 CandidateThesis 只贡献 6 个字段；probability 从 P5 引用（唯一来源）。
    """
    est = state.probability.t1 if horizon == "T+1" else state.probability.t2
    if est is None:
        raise ValueError(f"QuantState 无 {horizon} 概率")

    pr = ProbabilityReference(horizon=horizon, p_up=est.p_up, p_flat=est.p_flat, p_down=est.p_down)
    regime = {dim: dict(getattr(state.regime, dim))
              for dim in ("trend", "volatility", "macro", "event")}

    return TradingThesis(
        thesis_id=f"{state.symbol}-{state.as_of.date().isoformat()}-{horizon}-{run_id}",
        symbol=state.symbol, as_of=state.as_of, horizon=horizon,
        directional_bias=candidate.directional_bias,
        confidence=ThesisConfidence(score=candidate.confidence_score,
                                    level=candidate.confidence_level),
        probability_reference=pr,                       # 系统注入（P5 唯一来源）
        supporting_evidence=candidate.supporting_evidence,
        contradicting_evidence=candidate.contradicting_evidence,
        invalidation_conditions=candidate.invalidation_conditions,
        regime_snapshot=regime,                         # 系统注入（P4 引用）
        thesis_summary=candidate.thesis_summary,
        quant_state_version=state.state_version,        # 系统注入
        renderer_version=RENDERER_VERSION,              # 系统注入
        source_lineage=state.lineage,                   # 系统注入
        model_provenance=ModelProvenance(
            provider=provider, model=model, temperature=temperature,
            prompt_version=prompt_version, agent_version=agent_version, run_id=run_id,
        ),                                              # 系统注入
        created_at=state.as_of,                         # 系统注入
    )


class MockThesisLLM:
    """Deterministic mock：返回预设 candidate 或 raw JSON（用于测试，不调真实 API）。"""

    def __init__(self, candidate: CandidateThesis | None = None, raw: str | None = None):
        self._candidate = candidate
        self._raw = raw

    def generate(self, quant_context: str) -> CandidateThesis:
        if self._raw is not None:
            return parse_candidate(self._raw)   # malformed → ValidationError
        return self._candidate
