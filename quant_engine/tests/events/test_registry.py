# -*- coding: utf-8 -*-
"""Event Registry 完整性测试。"""
from quant_engine.events import EventRegistry


def test_events_registered():
    assert len(EventRegistry.all()) >= 24


def test_every_event_has_version_and_features():
    for d in EventRegistry.all():
        assert d.event_version, f"{d.event_name} 缺 version"
        assert d.input_features, f"{d.event_name} 缺 input_features"
        assert d.deduplication_rule in ("first_trigger_only", "cooldown")
        assert d.minimum_sample_size >= 30


def test_no_event_uses_label_fields():
    bad = {"future_return", "label"}
    for d in EventRegistry.all():
        assert not (set(d.input_features) & bad)
