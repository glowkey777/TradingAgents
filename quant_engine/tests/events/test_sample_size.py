# -*- coding: utf-8 -*-
"""Minimum Sample Size 门测试。"""
from quant_engine.events import detect_events
from quant_engine.events.validation import deduplicate, sample_size_gate


def test_insufficient_sample_marked():
    evs = deduplicate(detect_events("SPY", ["rsi_oversold"], start="2013-01-01", end="2026-09-25"))
    gate = sample_size_gate(evs, min_size=30)
    for name, status in gate.items():
        n = len([e for e in evs if e.event_name == name])
        if n < 30:
            assert status == "INSUFFICIENT_SAMPLE", f"{name} N={n} 应标记 INSUFFICIENT_SAMPLE"
        else:
            assert status == "SUFFICIENT", f"{name} N={n} 应标记 SUFFICIENT"


def test_no_zero_filled():
    # 样本不足时不得填 0 伪装成结论，状态必须是 INSUFFICIENT_SAMPLE
    evs = deduplicate(detect_events("SPY", ["macd_bullish_cross"], start="2024-01-01", end="2024-06-03"))
    gate = sample_size_gate(evs, min_size=30)
    assert all(v in ("SUFFICIENT", "INSUFFICIENT_SAMPLE") for v in gate.values())
