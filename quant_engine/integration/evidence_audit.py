# -*- coding: utf-8 -*-
"""Evidence Integrity Audit（STEP 5.11）。

对最终 TradingThesis 做 deterministic 审计：probability/regime/source/
unavailable/attribution/drift/invalidation/duplication 8 项完整性检查。
只读，不修改 frozen contract；LLM 若发生概率漂移、证据伪造、归因错误会被抓出。
"""
from __future__ import annotations

import re

from .thesis import TradingThesis
from .evidence_taxonomy import classify_source, EvidenceSource, NOT_AVAILABLE_FIELDS

TOL = 1e-6


def _all_evidence(thesis: TradingThesis):
    return list(thesis.supporting_evidence) + list(thesis.contradicting_evidence)


def _quant_probability_values(state) -> list[float]:
    out = []
    for h in ("t1", "t2"):
        est = getattr(state.probability, h)
        if est is not None:
            out += [est.p_up, est.p_flat, est.p_down]
    return out


def _quant_regime_values(state) -> list[float]:
    out = []
    for dim in ("trend", "volatility", "macro", "event"):
        out += list(dict(getattr(state.regime, dim)).values())
    return out


def _check_probability_integrity(thesis, state) -> dict:
    """final.p_up/p_flat/p_down 与 P5 严格相等（==，不是 ≈）。"""
    pr = thesis.probability_reference
    est = state.probability.t1 if thesis.horizon == "T+1" else state.probability.t2
    if est is None:
        return {"pass": False, "detail": [f"QuantState 无 {thesis.horizon} 概率"]}
    ok = (pr.p_up == est.p_up and pr.p_flat == est.p_flat and pr.p_down == est.p_down)
    detail = []
    if not ok:
        detail.append(f"final=({pr.p_up},{pr.p_flat},{pr.p_down}) vs P5=({est.p_up},{est.p_flat},{est.p_down})")
    return {"pass": ok, "detail": detail}


def _check_regime_integrity(thesis, state) -> dict:
    """thesis.regime_snapshot 与 P4 RegimeState 四维逐字段相等。"""
    errors = []
    for dim in ("trend", "volatility", "macro", "event"):
        thesis_dict = thesis.regime_snapshot.get(dim, {})
        state_dict = dict(getattr(state.regime, dim))
        if thesis_dict != state_dict:
            errors.append(f"{dim}: thesis={thesis_dict} vs P4={state_dict}")
    return {"pass": not errors, "detail": errors}


def _check_source_integrity(thesis, state, quant_context) -> dict:
    """Quant Engine evidence 的 source_id 必须能在 quant_context 中定位。

    用 meaningful token 匹配（点分/下划线分割，过滤类型词/horizon 词），
    避免 source_id 格式差异（如 P5_hierarchical_T1 vs EVIDENCE.P5 hierarchical T+1）
    造成假阳性。所有 meaningful token 都必须能在 quant_context 找到。
    """
    qc_low = (quant_context or "").lower()
    TYPE_WORDS = {"regime", "probability", "feature", "event", "risk", "market"}
    errors = []
    for ev in _all_evidence(thesis):
        if classify_source(ev.source_type) in (EvidenceSource.QUANT_ENGINE, EvidenceSource.RISK):
            tokens = [t for tok in re.split(r"[._\-]", ev.source_id.lower())
                      for t in re.findall(r"[a-z0-9]+", tok)]
            meaningful = [t for t in tokens if t and t not in TYPE_WORDS]
            if not meaningful:
                meaningful = [ev.source_id.lower()]
            missing = [t for t in meaningful if t not in qc_low]
            if missing:
                errors.append(f"evidence source_id '{ev.source_id}' 无法在 quant_context 定位（缺 {missing}）")
    return {"pass": not errors, "detail": errors}


def _check_unavailable_integrity(thesis) -> dict:
    """不得引用 QuantState 中 NOT_AVAILABLE 的字段（gamma/IV/breadth）。词边界匹配。"""
    errors = []
    for ev in _all_evidence(thesis):
        low = (ev.source_id + " " + ev.statement).lower()
        for field in NOT_AVAILABLE_FIELDS:
            pattern = r"(?<![a-z])" + re.escape(field) + r"(?![a-z])"
            if re.search(pattern, low):
                errors.append(f"evidence 引用 NOT_AVAILABLE 字段 '{field}'（source_id={ev.source_id}）")
    return {"pass": not errors, "detail": errors}


def _check_attribution_integrity(thesis) -> dict:
    """Agent 推理不能被标注为 Quant Engine 事实（source_type=quant_engine 但 statement 是推理）。"""
    inference_markers = ("i estimate", "i calculate", "i believe", "my analysis",
                         "i think", "i predict", "i expect", "in my view",
                         "i would", "my calculated")
    errors = []
    for ev in _all_evidence(thesis):
        if classify_source(ev.source_type) in (EvidenceSource.QUANT_ENGINE,):
            low = ev.statement.lower()
            for mk in inference_markers:
                if mk in low:
                    errors.append(f"attribution 错误：'{ev.source_id}' 标注 Quant Engine，但 statement 是 Agent 推理（'{mk}'）")
                    break
    return {"pass": not errors, "detail": errors}


def _check_drift_integrity(thesis, state) -> dict:
    """数值 drift：quant_engine 证据 statement 中的 0-1 数值必须匹配 QuantState 值。

    rounding（1-4 位）允许；P5 值的算术组合（两两和，如 FLAT+DOWN=0.5877）允许；
    实质偏离（如 0.4314 → 0.52）FAIL。
    """
    prob_vals = _quant_probability_values(state)
    regime_vals = _quant_regime_values(state)
    errors = []
    for ev in _all_evidence(thesis):
        if classify_source(ev.source_type) != EvidenceSource.QUANT_ENGINE:
            continue
        if ev.source_type == "probability":
            target = prob_vals
        elif ev.source_type == "regime":
            target = regime_vals
        else:
            target = prob_vals + regime_vals
        # 合法值集合：单个值 + 两两和（各含 rounding）
        valid = set()
        for v in target:
            for r in (4, 3, 2):
                valid.add(round(v, r))
        for i in range(len(target)):
            for j in range(i + 1, len(target)):
                s = target[i] + target[j]
                for r in (4, 3, 2):
                    valid.add(round(s, r))
        for m in re.findall(r"\d+\.\d+", ev.statement):
            v = float(m)
            if not (0.0 < v <= 1.0):
                continue
            if all(round(v, r) not in valid for r in (4, 3, 2)):
                errors.append(f"drift：'{ev.source_id}' statement 中 {v} 不匹配任何 QuantState 值")
                break
    return {"pass": not errors, "detail": errors}


def _check_invalidation_integrity(thesis, state, quant_context, context_sources="") -> dict:
    """invalidation 中的价格必须能溯源到 market 数据（close/open/high/low）或 agent 工具输出（SMA/EMA 等）。"""
    m = state.market
    prices = [p for p in (m.close, m.open, m.high, m.low) if p is not None]
    src = (quant_context or "") + " " + (context_sources or "")
    errors = []
    for inv in thesis.invalidation_conditions:
        for num in re.findall(r"\d+\.\d+", inv):
            v = float(num)
            if not any(abs(v - p) < 1.0 for p in prices):
                # 不在 QuantState.market，检查是否在 quant_context / agent 工具输出里
                if str(round(v, 1)) not in src and str(round(v, 2)) not in src and str(round(v)) not in src:
                    errors.append(f"invalidation 价格 {v} 无法溯源到 market 数据或 agent 工具输出")
    return {"pass": not errors, "detail": errors}


def _check_duplication_integrity(thesis) -> dict:
    """supporting/contradicting 无重复 evidence（同一 source_id+statement 改写充数）。"""
    errors = []
    seen = set()
    for ev in _all_evidence(thesis):
        key = (ev.source_type, ev.source_id, ev.statement.strip().lower())
        if key in seen:
            errors.append(f"重复 evidence：source_id={ev.source_id}")
        seen.add(key)
    return {"pass": not errors, "detail": errors}


def validate_thesis_evidence_integrity(thesis: TradingThesis, state, quant_context: str = "",
                                       context_sources: str = "") -> dict:
    """8 项证据完整性审计。返回 {项名: {pass: bool, detail: list}}。

    context_sources: agent 工具输出的额外可溯源文本（如 market_report 的 SMA/EMA），
    用于 invalidation 价格溯源。默认空（单测场景）。"""
    return {
        "probability_integrity": _check_probability_integrity(thesis, state),
        "regime_integrity": _check_regime_integrity(thesis, state),
        "source_integrity": _check_source_integrity(thesis, state, quant_context),
        "unavailable_integrity": _check_unavailable_integrity(thesis),
        "attribution_integrity": _check_attribution_integrity(thesis),
        "drift_integrity": _check_drift_integrity(thesis, state),
        "invalidation_integrity": _check_invalidation_integrity(thesis, state, quant_context, context_sources),
        "duplication_integrity": _check_duplication_integrity(thesis),
    }
