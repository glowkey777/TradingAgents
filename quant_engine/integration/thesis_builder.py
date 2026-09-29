# -*- coding: utf-8 -*-
"""QuantState → TradingThesis 的 deterministic initialization（STEP 5.4）。

只初始化 Contract 骨架 + 从 QuantState 引用（probability/regime/lineage），
directional_bias / thesis_summary / confidence 留待 LLM（STEP 5.7）填充。
不重新计算任何量化值。
"""
from __future__ import annotations

from datetime import datetime

from quant_engine.state.models import QuantState

from .renderer import RENDERER_VERSION
from .thesis import (
    TradingThesis, DirectionalBias, ThesisConfidence, ProbabilityReference,
    ModelProvenance,
)


def init_thesis(
    state: QuantState,
    horizon: str,
    run_id: str,
    provider: str,
    model: str,
    prompt_version: str,
    agent_version: str,
    temperature: float | None = None,
) -> TradingThesis:
    """从 QuantState 构建 TradingThesis 骨架（directional_bias 默认 NEUTRAL 待 LLM 覆盖）。"""
    est = state.probability.t1 if horizon == "T+1" else state.probability.t2
    if est is None:
        raise ValueError(f"QuantState 无 {horizon} 概率，无法初始化 Thesis")

    pr = ProbabilityReference(horizon=horizon, p_up=est.p_up, p_flat=est.p_flat, p_down=est.p_down)
    regime = {dim: dict(getattr(state.regime, dim))
              for dim in ("trend", "volatility", "macro", "event")}

    return TradingThesis(
        thesis_id=f"{state.symbol}-{state.as_of.date().isoformat()}-{horizon}-{run_id}",
        symbol=state.symbol, as_of=state.as_of, horizon=horizon,
        directional_bias=DirectionalBias.NEUTRAL,          # 待 LLM 覆盖
        confidence=ThesisConfidence(score=0.0, level="low"),  # 待 LLM 覆盖
        probability_reference=pr,
        regime_snapshot=regime,
        quant_state_version=state.state_version,
        renderer_version=RENDERER_VERSION,
        source_lineage=state.lineage,
        model_provenance=ModelProvenance(
            provider=provider, model=model, temperature=temperature,
            prompt_version=prompt_version, agent_version=agent_version, run_id=run_id,
        ),
        created_at=state.as_of,                            # 确定性，不用 now()
    )
