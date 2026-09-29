# -*- coding: utf-8 -*-
"""Decision Quality Audit（P7 STEP 5.12）。

9 维决策质量闸门：回答「最终 TradingThesis 是否是结构完整、证据一致、
概率受 P5 约束、provenance 完整、invalidation 完整、可审计的决策对象」。

只读，不修改 frozen contract。组合现有 validate_thesis + evidence_audit，
新增 schema completeness / thesis completeness / direction consistency /
provenance completeness / system-field determinism。

注意（STEP 5.12 语义）：
- 不检查「方向是否等于 P5 最大概率类别」——P5 是 reference 不是 LLM 答案。
- 不要求 LLM 自由文本逐字符 deterministic——只检查 system-owned 字段。
"""
from __future__ import annotations

from .thesis import TradingThesis, DirectionalBias
from .evidence_audit import validate_thesis_evidence_integrity


# ── 1. Schema completeness ──
REQUIRED_FIELDS = (
    "thesis_id", "as_of", "symbol", "horizon", "directional_bias", "confidence",
    "probability_reference", "supporting_evidence", "contradicting_evidence",
    "invalidation_conditions", "regime_snapshot", "quant_state_version",
    "renderer_version", "source_lineage", "model_provenance",
)


def _check_schema_completeness(thesis: TradingThesis) -> dict:
    missing = [k for k in REQUIRED_FIELDS if getattr(thesis, k, None) in (None, "", {})]
    return {"pass": not missing, "detail": [f"{k} 缺失" for k in missing]}


# ── 2. Probability binding ──
def _check_probability_binding(thesis: TradingThesis, state) -> dict:
    pr = thesis.probability_reference
    est = state.probability.t1 if thesis.horizon == "T+1" else state.probability.t2
    errors = []
    if est is None:
        return {"pass": False, "detail": [f"QuantState 无 {thesis.horizon} 概率"]}
    if pr.horizon != est.horizon:
        errors.append(f"horizon: {pr.horizon} != {est.horizon}")
    for name in ("p_up", "p_flat", "p_down"):
        a, b = getattr(pr, name), getattr(est, name)
        if a != b:  # 严格 ==，不接受近似
            errors.append(f"{name}: final={a} != P5={b}")
    # P5 method/sample_size/status/version 完整性（final 不引用这些字段，但 P5 本身必须完整）
    if not est.method or not est.probability_version:
        errors.append("P5 method/probability_version 缺失")
    if est.sample_size is None or est.sample_size <= 0:
        errors.append("P5 sample_size 缺失/无效")
    if not est.status:
        errors.append("P5 status 缺失")
    # version metadata binding：quant_state_version 追溯回 P6
    if thesis.quant_state_version != state.state_version:
        errors.append(f"quant_state_version {thesis.quant_state_version} != P6 {state.state_version}")
    return {"pass": not errors, "detail": errors}


# ── 3. Regime binding ──
def _check_regime_binding(thesis: TradingThesis, state) -> dict:
    errors = []
    for dim in ("trend", "volatility", "macro", "event"):
        thesis_dict = thesis.regime_snapshot.get(dim, {})
        state_dict = dict(getattr(state.regime, dim))
        if thesis_dict != state_dict:
            errors.append(f"{dim}: thesis={thesis_dict} vs P4={state_dict}")
    return {"pass": not errors, "detail": errors}


# ── 4. Evidence integrity（复用 STEP 5.11） ──
def _check_evidence_integrity(thesis, state, quant_context, context_sources) -> dict:
    audit = validate_thesis_evidence_integrity(thesis, state, quant_context, context_sources)
    failed = [k for k, v in audit.items() if not v["pass"]]
    return {"pass": not failed, "detail": [f"{k} FAIL" for k in failed]}


# ── 5. Thesis completeness ──
def _check_thesis_completeness(thesis: TradingThesis) -> dict:
    errors = []
    if not thesis.supporting_evidence:
        errors.append("supporting_evidence 为空")
    if not thesis.contradicting_evidence:
        errors.append("contradicting_evidence 为空（必须存在反方/限制因素）")
    if not thesis.invalidation_conditions:
        errors.append("invalidation_conditions 为空（thesis 必须可证伪）")
    if not thesis.thesis_summary.strip():
        errors.append("thesis_summary 为空")
    return {"pass": not errors, "detail": errors}


# ── 6. Direction / evidence consistency ──
def _explicitly_bullish(text: str) -> bool:
    return any(m in text for m in ("bullish", "uptrend", "upward", "rally",
                                   "expect a rise", "expect the price to rise",
                                   "breakout to the upside", "upside bias"))


def _explicitly_bearish(text: str) -> bool:
    return any(m in text for m in ("bearish", "downtrend", "downward", "decline",
                                   "expect a decline", "expect the price to fall",
                                   "breakdown", "downside bias"))


def _check_direction_consistency(thesis: TradingThesis) -> dict:
    """审计 directional_bias 与 thesis_summary 的内部逻辑矛盾。

    不检查「方向 != P5 最大概率类别」（P5 是 reference 不是 LLM 答案）。
    只检查 thesis 自身陈述（summary）是否与 bias 直接矛盾。
    """
    errors = []
    summary = (thesis.thesis_summary or "").lower()
    bias = thesis.directional_bias
    if bias == DirectionalBias.BULLISH and _explicitly_bearish(summary):
        errors.append("directional_bias=BULLISH 但 thesis_summary 明确 bearish")
    elif bias == DirectionalBias.BEARISH and _explicitly_bullish(summary):
        errors.append("directional_bias=BEARISH 但 thesis_summary 明确 bullish")
    return {"pass": not errors, "detail": errors}


# ── 7. Invalidation traceability（复用 STEP 5.11 context_sources 机制） ──
def _check_invalidation_traceability(thesis, state, quant_context, context_sources) -> dict:
    audit = validate_thesis_evidence_integrity(thesis, state, quant_context, context_sources)
    return audit["invalidation_integrity"]


# ── 8. Provenance completeness ──
def _check_provenance_completeness(thesis: TradingThesis) -> dict:
    mp = thesis.model_provenance
    errors = []
    for name in ("provider", "model", "prompt_version", "agent_version", "run_id"):
        if not getattr(mp, name):
            errors.append(f"provenance.{name} 缺失")
    if mp.temperature is None:
        errors.append("provenance.temperature 未显式配置（Golden run 应显式）")
    if thesis.as_of is None:
        errors.append("as_of 缺失")
    if not thesis.quant_state_version:
        errors.append("quant_state_version 缺失")
    if not thesis.renderer_version:
        errors.append("renderer_version 缺失")
    return {"pass": not errors, "detail": errors}


# ── 9. Determinism of system-owned fields ──
def _check_system_field_determinism(thesis: TradingThesis, state) -> dict:
    """system-owned 字段必须由 QuantState + 系统参数确定性推导，非 LLM 影响、非随机。"""
    errors = []
    if thesis.as_of != state.as_of:
        errors.append(f"as_of {thesis.as_of} != state.as_of")
    if thesis.created_at != state.as_of:
        errors.append(f"created_at {thesis.created_at} != state.as_of（应为 state.as_of 而非 now()）")
    if thesis.symbol != state.symbol:
        errors.append(f"symbol {thesis.symbol} != {state.symbol}")
    if thesis.quant_state_version != state.state_version:
        errors.append(f"quant_state_version {thesis.quant_state_version} != {state.state_version}")
    if thesis.source_lineage != state.lineage:
        errors.append("source_lineage != state.lineage")
    return {"pass": not errors, "detail": errors}


# ── 汇总 ──
def audit_decision_quality(thesis: TradingThesis, state, quant_context: str = "",
                           context_sources: str = "") -> dict:
    """9 维决策质量审计。返回 {维度: {pass: bool, detail: list}}。"""
    return {
        "schema_completeness": _check_schema_completeness(thesis),
        "probability_binding": _check_probability_binding(thesis, state),
        "regime_binding": _check_regime_binding(thesis, state),
        "evidence_integrity": _check_evidence_integrity(thesis, state, quant_context, context_sources),
        "thesis_completeness": _check_thesis_completeness(thesis),
        "direction_consistency": _check_direction_consistency(thesis),
        "invalidation_traceability": _check_invalidation_traceability(thesis, state, quant_context, context_sources),
        "provenance_completeness": _check_provenance_completeness(thesis),
        "system_field_determinism": _check_system_field_determinism(thesis, state),
    }


def validate_decision_quality(thesis: TradingThesis, state, quant_context: str = "",
                              context_sources: str = "") -> list[str]:
    """返回 FAIL 的维度名列表；空 = 全 PASS。"""
    audit = audit_decision_quality(thesis, state, quant_context, context_sources)
    return [k for k, v in audit.items() if not v["pass"]]
