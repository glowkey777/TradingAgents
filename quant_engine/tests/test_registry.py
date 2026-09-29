# -*- coding: utf-8 -*-
"""Registry 完整性测试。"""
from quant_engine.features.registry import FeatureRegistry


def test_features_registered():
    assert len(FeatureRegistry.all()) >= 78


def test_every_feature_has_version_and_formula():
    for d in FeatureRegistry.all():
        assert d.feature_version, f"{d.feature_name} 缺 version"
        assert d.formula, f"{d.feature_name} 缺 formula"
        assert d.input_fields, f"{d.feature_name} 缺 input_fields"
        assert d.frequency, f"{d.feature_name} 缺 frequency"


def test_no_duplicate_names():
    names = [d.feature_name for d in FeatureRegistry.all()]
    assert len(names) == len(set(names))


def test_frequencies():
    freqs = {d.frequency for d in FeatureRegistry.all()}
    assert {"daily", "15m", "session"} <= freqs
