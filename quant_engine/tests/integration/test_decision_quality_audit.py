# -*- coding: utf-8 -*-
"""Decision Quality Audit 测试（STEP 5.12-C）：12 个 adversarial cases。"""
import pytest

from quant_engine.integration.thesis import TradingThesis, EvidenceReference, DirectionalBias
from quant_engine.integration.thesis_llm_adapter import CandidateThesis, assemble_thesis
from quant_engine.integration.decision_quality_audit import (
    audit_decision_quality, validate_decision_quality,
)

RUN_ID = "run-dq"
TEMPERATURE = 0.2


def _candidate(**kw):
    base = dict(
        directional_bias=DirectionalBias.BULLISH,
        thesis_summary="Bull trend dominates with low volatility supporting upside bias.",
        confidence_score=0.6, confidence_level="medium",
        supporting_evidence=[
            EvidenceReference(source_type="regime", source_id="REGIME.Trend.bull_trend",
                              statement="bull_trend 0.8333 dominates"),
        ],
        contradicting_evidence=[
            EvidenceReference(source_type="probability", source_id="PROBABILITY.T1",
                              statement="T1 FLAT 0.4314 limits near-term conviction"),
        ],
        invalidation_conditions=["跌破 505 则证伪"],
    )
    base.update(kw)
    return CandidateThesis(**base)


def _assemble(state, cand=None):
    return assemble_thesis(cand or _candidate(), state, "T+1", RUN_ID, "deepseek",
                           "deepseek-v4-pro", "research_prompt_v1", "quant_analyst_v1", TEMPERATURE)


def _mutate(thesis, **updates):
    data = thesis.model_dump()
    data.update(updates)
    return TradingThesis.model_validate(data)


# ── 12. 正常完整 thesis → 全 PASS ──
def test_normal_thesis_all_pass(state, quant_context):
    t = _assemble(state)
    assert validate_decision_quality(t, state, quant_context) == []


# ── 1. LLM 修改 p_up → probability 必须仍来自 P5 ──
def test_llm_modified_p_up(state):
    t = _assemble(state)
    bad = _mutate(t, probability_reference={"horizon": "T+1", "p_up": 0.52,
                                            "p_flat": 0.24, "p_down": 0.24})
    assert "probability_binding" in validate_decision_quality(bad, state)


# ── 2. LLM 修改 regime → regime 必须仍来自 P4 ──
def test_llm_modified_regime(state):
    t = _assemble(state)
    data = t.model_dump()
    data["regime_snapshot"]["trend"]["bull_trend"] = 0.5
    bad = TradingThesis.model_validate(data)
    assert "regime_binding" in validate_decision_quality(bad, state)


# ── 3. LLM 删除 invalidation → FAIL ──
def test_llm_deleted_invalidation(state):
    t = _assemble(state, _candidate(invalidation_conditions=[]))
    assert "thesis_completeness" in validate_decision_quality(t, state)


# ── 4. LLM 删除 contradicting evidence → FAIL ──
def test_llm_deleted_contradicting(state):
    t = _assemble(state, _candidate(contradicting_evidence=[]))
    assert "thesis_completeness" in validate_decision_quality(t, state)


# ── 5. LLM 添加不存在的 gamma → evidence audit FAIL ──
def test_llm_fabricated_gamma(state):
    t = _assemble(state, _candidate(supporting_evidence=[
        EvidenceReference(source_type="feature", source_id="gamma_wall",
                          statement="gamma is strongly positive")]))
    assert "evidence_integrity" in validate_decision_quality(t, state)


# ── 6. LLM 添加第二套 probability → FAIL ──
def test_llm_second_probability(state):
    t = _assemble(state, _candidate(supporting_evidence=[
        EvidenceReference(source_type="probability", source_id="PROBABILITY.T1",
                          statement="my own estimate P(up) = 0.63")]))
    assert "evidence_integrity" in validate_decision_quality(t, state)


# ── 7. LLM 修改 lineage → system-owned 不变 / FAIL ──
def test_llm_modified_lineage(state):
    t = _assemble(state)
    data = t.model_dump()
    data["source_lineage"]["pipeline_version"] = "hacked_v1"
    bad = TradingThesis.model_validate(data)
    assert "system_field_determinism" in validate_decision_quality(bad, state)


# ── 8. LLM 修改 provenance → FAIL tampering ──
def test_llm_modified_provenance(state):
    t = _assemble(state)
    data = t.model_dump()
    data["model_provenance"]["run_id"] = ""
    bad = TradingThesis.model_validate(data)
    assert "provenance_completeness" in validate_decision_quality(bad, state)


# ── 9. directional_bias 与自身陈述内部矛盾 → FAIL ──
def test_internal_direction_contradiction(state):
    t = _assemble(state, _candidate(
        directional_bias=DirectionalBias.BULLISH,
        thesis_summary="This is clearly a bearish downtrend with strong decline expected."))
    assert "direction_consistency" in validate_decision_quality(t, state)


# ── 10. invalidation 使用不存在的关键价格 → FAIL ──
def test_invalidation_bogus_price(state):
    t = _assemble(state, _candidate(invalidation_conditions=["跌破 999.99 则证伪"]))
    assert "invalidation_traceability" in validate_decision_quality(t, state)


# ── 11. 空 thesis（缺 required 字段）→ FAIL ──
def test_empty_thesis(state):
    t = _assemble(state)
    data = t.model_dump()
    data["thesis_id"] = ""
    data["symbol"] = ""
    data["thesis_summary"] = ""
    bad = TradingThesis.model_validate(data)
    assert "schema_completeness" in validate_decision_quality(bad, state)
