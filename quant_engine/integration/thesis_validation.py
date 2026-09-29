# -*- coding: utf-8 -*-
"""TradingThesis 验证：结构 / 概率和 / 越界 / 伪造 / lineage / provenance。"""
from __future__ import annotations

from .thesis import TradingThesis


def validate_thesis(thesis: TradingThesis) -> list[str]:
    errors: list[str] = []

    # 结构
    if not thesis.thesis_id:
        errors.append("thesis_id 缺失")
    if not thesis.symbol:
        errors.append("symbol 缺失")
    if thesis.as_of is None:
        errors.append("as_of 缺失")
    if not thesis.horizon:
        errors.append("horizon 缺失")

    # probability 和 = 1（已由 model_validator 保证，这里 double-check 越界）
    pr = thesis.probability_reference
    s = pr.p_up + pr.p_flat + pr.p_down
    if abs(s - 1.0) > 1e-6:
        errors.append(f"probability 和={s} != 1")

    # confidence 越界（Field ge/le 已保证，double-check）
    if thesis.confidence.score < 0 or thesis.confidence.score > 1:
        errors.append(f"confidence.score={thesis.confidence.score} 越界 [0,1]")

    # directional_bias 合法性（Enum 已保证，但检查是否为有效枚举）
    if thesis.directional_bias not in ("bullish", "bearish", "neutral", "mixed"):
        errors.append(f"invalid directional_bias={thesis.directional_bias}")

    # 追溯
    if not thesis.quant_state_version:
        errors.append("quant_state_version 缺失")
    if not thesis.renderer_version:
        errors.append("renderer_version 缺失")
    if not thesis.source_lineage.pipeline_version:
        errors.append("source_lineage 不完整")

    # provenance
    mp = thesis.model_provenance
    if not mp.provider or not mp.model or not mp.prompt_version:
        errors.append("model_provenance 缺失（provider/model/prompt_version）")
    if not mp.run_id:
        errors.append("provenance.run_id 缺失")

    # invalidation 必须有（否则 thesis 无法证伪）
    if not thesis.invalidation_conditions:
        errors.append("invalidation_conditions 缺失（thesis 必须可证伪）")

    return errors


def check_confidence_not_probability(thesis: TradingThesis) -> list[str]:
    """confidence ≠ p_up/p_flat/p_down（LLM 不得照抄概率值当置信度）。"""
    pr = thesis.probability_reference
    c = thesis.confidence.score
    for name, v in (("p_up", pr.p_up), ("p_flat", pr.p_flat), ("p_down", pr.p_down)):
        if c is not None and abs(c - v) < 1e-9:
            return [f"confidence.score={c} 精确等于 {name}，混淆 confidence 与概率"]
    return []


def check_fabricated_evidence(thesis: TradingThesis, state) -> list[str]:
    """LLM 不得引用 QuantState 中 NOT_AVAILABLE 的数据（P7 硬边界）。"""
    errors: list[str] = []
    avail_features = state.features.values if state is not None else {}
    for ev in thesis.supporting_evidence + thesis.contradicting_evidence:
        if ev.source_type == "feature":
            if ev.source_id not in avail_features or avail_features.get(ev.source_id) is None:
                errors.append(f"伪造证据：feature '{ev.source_id}' 在 QuantState 中 NOT_AVAILABLE")
        elif ev.source_type in ("risk", "gamma", "iv", "breadth"):
            # P6 中 gamma/iv/breadth 未实现，Risk=NOT_AVAILABLE
            errors.append(f"伪造证据：'{ev.source_id}' 在 QuantState 中 NOT_AVAILABLE")
    return errors
