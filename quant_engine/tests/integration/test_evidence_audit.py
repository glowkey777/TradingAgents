# -*- coding: utf-8 -*-
"""Evidence Integrity Audit 测试（STEP 5.11）：正常 + 8 项异常。"""
import pytest

from quant_engine.integration.thesis import TradingThesis, EvidenceReference, DirectionalBias
from quant_engine.integration.thesis_llm_adapter import CandidateThesis, assemble_thesis
from quant_engine.integration.evidence_audit import validate_thesis_evidence_integrity


def _candidate(**kw):
    base = dict(directional_bias=DirectionalBias.BULLISH, thesis_summary="偏多",
                confidence_score=0.6, confidence_level="medium",
                invalidation_conditions=["跌破 505 则证伪"])
    base.update(kw)
    return CandidateThesis(**base)


def _assemble(state, cand):
    return assemble_thesis(cand, state, "T+1", "run-x", "deepseek",
                           "deepseek-v4-pro", "p1", "a1", 0.2)


def _with(thesis, **updates):
    data = thesis.model_dump()
    data.update(updates)
    return TradingThesis.model_validate(data)


# ── 正常 case：8 项全 PASS ──
def test_integrity_all_pass(state, quant_context):
    t = _assemble(state, _candidate(
        supporting_evidence=[
            EvidenceReference(source_type="regime", source_id="REGIME.Trend.bull_trend",
                              statement="bull_trend 0.8333 dominates"),
            EvidenceReference(source_type="probability", source_id="PROBABILITY.T1",
                              statement="T1 FLAT 0.4314 is highest"),
        ]))
    audit = validate_thesis_evidence_integrity(t, state, quant_context)
    assert all(v["pass"] for v in audit.values()), audit


# A. probability integrity：改 p_up → FAIL
def test_probability_drift(state):
    t = _assemble(state, _candidate())
    t_bad = _with(t, probability_reference={"horizon": "T+1", "p_up": 0.52,
                                            "p_flat": 0.24, "p_down": 0.24})
    assert not validate_thesis_evidence_integrity(t_bad, state, "")["probability_integrity"]["pass"]


# B. regime integrity：改 regime_snapshot → FAIL
def test_regime_drift(state):
    t = _assemble(state, _candidate())
    data = t.model_dump()
    data["regime_snapshot"]["trend"]["bull_trend"] = 0.5
    t_bad = TradingThesis.model_validate(data)
    assert not validate_thesis_evidence_integrity(t_bad, state, "")["regime_integrity"]["pass"]


# C. source integrity：source_id 不可溯源 → FAIL
def test_source_not_traceable(state, quant_context):
    t = _assemble(state, _candidate(supporting_evidence=[
        EvidenceReference(source_type="regime", source_id="REGIME.Trend.nonexistent_field")]))
    assert not validate_thesis_evidence_integrity(t, state, quant_context)["source_integrity"]["pass"]


# D. unavailable integrity：引用 gamma → FAIL
def test_unavailable_field(state):
    t = _assemble(state, _candidate(supporting_evidence=[
        EvidenceReference(source_type="feature", source_id="gamma_wall",
                          statement="gamma is strongly positive")]))
    assert not validate_thesis_evidence_integrity(t, state, "")["unavailable_integrity"]["pass"]


# E. attribution integrity：Agent 推理写成 Quant Engine → FAIL
def test_attribution_error(state):
    t = _assemble(state, _candidate(supporting_evidence=[
        EvidenceReference(source_type="probability", source_id="PROBABILITY.T1",
                          statement="I estimate the probability is 60% up")]))
    assert not validate_thesis_evidence_integrity(t, state, "")["attribution_integrity"]["pass"]


# F. drift integrity：statement 数值偏离 → FAIL
def test_numeric_drift(state):
    t = _assemble(state, _candidate(supporting_evidence=[
        EvidenceReference(source_type="probability", source_id="PROBABILITY.T1",
                          statement="FLAT probability is 0.52")]))
    assert not validate_thesis_evidence_integrity(t, state, "")["drift_integrity"]["pass"]


# G. invalidation integrity：价格不可溯源 → FAIL
def test_invalidation_not_traceable(state):
    t = _assemble(state, _candidate(invalidation_conditions=["跌破 999.99 则证伪"]))
    assert not validate_thesis_evidence_integrity(t, state, "")["invalidation_integrity"]["pass"]


# H. duplication integrity：重复 evidence → FAIL
def test_duplication(state):
    ev = EvidenceReference(source_type="regime", source_id="REGIME.Trend.bull_trend",
                           statement="bull_trend dominates")
    t = _assemble(state, _candidate(supporting_evidence=[ev, ev]))
    assert not validate_thesis_evidence_integrity(t, state, "")["duplication_integrity"]["pass"]
