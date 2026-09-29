# -*- coding: utf-8 -*-
"""TradingThesis 模型测试：round-trip + init + determinism。"""
from datetime import datetime

from quant_engine.integration.thesis_builder import init_thesis
from quant_engine.integration.thesis import TradingThesis, DirectionalBias


def test_round_trip(thesis):
    j = thesis.model_dump_json()
    assert TradingThesis.model_validate_json(j) == thesis


def test_init_from_quantstate(thesis, state):
    assert thesis.symbol == "SPY"
    assert thesis.quant_state_version == state.state_version
    assert thesis.renderer_version == "quant_context_v1"
    assert thesis.source_lineage == state.lineage
    # probability_reference 引用 P5，不重新计算
    assert thesis.probability_reference.p_up == state.probability.t1.p_up
    # regime_snapshot 引用 P4 四维
    assert set(thesis.regime_snapshot.keys()) == {"trend", "volatility", "macro", "event"}


def test_init_deterministic(state):
    a = init_thesis(state, "T+1", "r1", "deepseek", "m", "p1", "a1")
    b = init_thesis(state, "T+1", "r1", "deepseek", "m", "p1", "a1")
    assert a.model_dump_json() == b.model_dump_json()


def test_confidence_not_equal_probability(thesis, state):
    # 初始 confidence.score=0.0（待 LLM），p_up 独立 —— 两者语义分离
    assert thesis.confidence.score != thesis.probability_reference.p_up
