# -*- coding: utf-8 -*-
"""Thesis LLM Adapter 测试：valid case + 10 adversarial cases（STEP 5.7-C/D）。"""
import pytest
from pydantic import ValidationError

from quant_engine.integration.thesis import DirectionalBias, EvidenceReference
from quant_engine.integration.thesis_llm_adapter import (
    CandidateThesis, parse_candidate, assemble_thesis,
)
from quant_engine.integration.thesis_validation import (
    validate_thesis, check_fabricated_evidence, check_confidence_not_probability,
)


def _candidate(**kw):
    base = dict(directional_bias=DirectionalBias.BULLISH, thesis_summary="偏多",
                confidence_score=0.6, confidence_level="medium",
                invalidation_conditions=["跌破 505 则证伪"])
    base.update(kw)
    return CandidateThesis(**base)


def _assemble(candidate, state):
    return assemble_thesis(candidate, state, "T+1", "run-x", "deepseek",
                           "deepseek-v4-pro", "research_prompt_v1", "quant_analyst_v1")


# Case 1：正常结构化 Thesis → PASS
def test_case1_valid_thesis(state):
    t = _assemble(_candidate(), state)
    assert validate_thesis(t) == []
    assert check_confidence_not_probability(t) == []
    assert check_fabricated_evidence(t, state) == []


# Case 2：p_up 被 LLM 自己修改 → 系统覆盖（CandidateThesis 无 p_up 字段，忽略）
def test_case2_llm_cannot_change_probability(state):
    raw = '{"directional_bias":"bullish","confidence_score":0.6,"confidence_level":"medium",' \
          '"invalidation_conditions":["x"],"p_up":0.99,"p_flat":0.005,"p_down":0.005}'
    cand = parse_candidate(raw)                      # p_up 被忽略（非 CandidateThesis 字段）
    t = _assemble(cand, state)
    assert t.probability_reference.p_up == state.probability.t1.p_up  # 系统用 P5 值


# Case 3：fabricated gamma → REJECT
def test_case3_fabricated_gamma(state):
    cand = _candidate(supporting_evidence=[
        EvidenceReference(source_type="feature", source_id="gamma_wall_25d")])
    t = _assemble(cand, state)
    assert check_fabricated_evidence(t, state)


# Case 4：fabricated IV → REJECT
def test_case4_fabricated_iv(state):
    cand = _candidate(supporting_evidence=[
        EvidenceReference(source_type="feature", source_id="implied_volatility")])
    t = _assemble(cand, state)
    assert check_fabricated_evidence(t, state)


# Case 5：NOT_AVAILABLE 被当 0/evidence → REJECT
def test_case5_not_available_as_evidence(state):
    cand = _candidate(supporting_evidence=[
        EvidenceReference(source_type="risk", source_id="tail_risk_99")])
    t = _assemble(cand, state)
    assert check_fabricated_evidence(t, state)


# Case 6：lineage 被 LLM 修改 → 系统覆盖（CandidateThesis 无 lineage）
def test_case6_llm_cannot_change_lineage(state):
    t = _assemble(_candidate(), state)
    assert t.source_lineage == state.lineage
    assert t.quant_state_version == state.state_version


# Case 7：confidence = p_up → REJECT
def test_case7_confidence_equals_p_up(state):
    p_up = state.probability.t1.p_up
    cand = _candidate(confidence_score=p_up)   # LLM 照抄概率
    t = _assemble(cand, state)
    assert check_confidence_not_probability(t)


# Case 8：概率和 ≠ 1 → 系统注入恒成立（无法违反）
def test_case8_probability_sum_is_one(state):
    t = _assemble(_candidate(), state)
    pr = t.probability_reference
    assert abs(pr.p_up + pr.p_flat + pr.p_down - 1) < 1e-9


# Case 9：缺 invalidation → REJECT
def test_case9_missing_invalidation(state):
    cand = _candidate(invalidation_conditions=[])
    t = _assemble(cand, state)
    assert any("invalidation" in e for e in validate_thesis(t))


# Case 10：malformed JSON → REJECT
def test_case10_malformed_json(state):
    with pytest.raises(ValidationError):
        parse_candidate('{"directional_bias": "bullish", "confidence_score": ')


def test_mock_llm_returns_candidate(state):
    from quant_engine.integration.thesis_llm_adapter import MockThesisLLM
    llm = MockThesisLLM(candidate=_candidate())
    cand = llm.generate("quant_context...")
    assert cand.directional_bias == DirectionalBias.BULLISH
