# -*- coding: utf-8 -*-
"""TradingThesis negative tests（STEP 5.6）。"""
import pytest

from quant_engine.integration.thesis import (
    TradingThesis, ProbabilityReference, ThesisConfidence, EvidenceReference,
    ModelProvenance, StateLineage,
)
from quant_engine.integration.thesis_validation import validate_thesis, check_fabricated_evidence


def test_probability_sum_must_be_one(thesis):
    data = thesis.model_dump()
    data["probability_reference"] = {"horizon": "T+1", "p_up": 0.5, "p_flat": 0.4, "p_down": 0.4}
    with pytest.raises(Exception):
        TradingThesis.model_validate(data)


def test_probability_negative(thesis):
    data = thesis.model_dump()
    data["probability_reference"] = {"horizon": "T+1", "p_up": -0.1, "p_flat": 0.6, "p_down": 0.5}
    with pytest.raises(Exception):
        TradingThesis.model_validate(data)


def test_confidence_out_of_range():
    with pytest.raises(Exception):
        ThesisConfidence(score=1.5, level="high")


def test_invalid_directional_bias(thesis):
    data = thesis.model_dump()
    data["directional_bias"] = "SIDEWAYS"
    with pytest.raises(Exception):
        TradingThesis.model_validate(data)


def test_missing_quant_state_version(thesis):
    bad = thesis.model_copy(update={"quant_state_version": ""})
    assert any("quant_state_version" in e for e in validate_thesis(bad))


def test_missing_provenance(thesis):
    bad = thesis.model_copy(update={"model_provenance": ModelProvenance(
        provider="", model="", prompt_version="", agent_version="a", run_id="r")})
    assert any("provenance" in e for e in validate_thesis(bad))


def test_missing_lineage(thesis):
    empty = StateLineage(
        data_versions={}, feature_version="", event_version="", regime_version="",
        probability_version="", risk_version="", source_versions={}, pipeline_version="")
    bad = thesis.model_copy(update={"source_lineage": empty})
    assert any("lineage" in e for e in validate_thesis(bad))


def test_fabricated_unavailable_feature(thesis, state):
    t = thesis.model_copy(update={"supporting_evidence": [
        EvidenceReference(source_type="feature", source_id="gamma_wall_25d", statement="Gamma wall strong")]})
    assert check_fabricated_evidence(t, state)


def test_fabricated_risk(thesis, state):
    t = thesis.model_copy(update={"contradicting_evidence": [
        EvidenceReference(source_type="risk", source_id="tail_risk_99", statement="tail risk high")]})
    assert check_fabricated_evidence(t, state)
