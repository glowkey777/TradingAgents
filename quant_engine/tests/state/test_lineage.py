# -*- coding: utf-8 -*-
"""Lineage 测试。"""
from quant_engine.state.lineage import FEATURE_VERSION, EVENT_VERSION, REGIME_VERSION, \
    PROBABILITY_VERSION, PIPELINE_VERSION


def test_lineage_complete(state_2024):
    L = state_2024.lineage
    assert L.pipeline_version == PIPELINE_VERSION
    assert L.feature_version == FEATURE_VERSION
    assert L.event_version == EVENT_VERSION
    assert L.regime_version == REGIME_VERSION
    assert L.probability_version == PROBABILITY_VERSION
    assert L.label_version is not None
    assert L.data_versions


def test_versions_match_snapshots(state_2024):
    assert state_2024.features.feature_version == state_2024.lineage.feature_version
    assert state_2024.regime.regime_version == state_2024.lineage.regime_version
