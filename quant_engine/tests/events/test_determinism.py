# -*- coding: utf-8 -*-
"""Event Study Determinism 测试。"""
from quant_engine.events import run_event_study


def test_deterministic_study():
    a = run_event_study(event_names=["large_down_day", "vix_shock_up"],
                        start="2020-01-01", end="2024-06-03")
    b = run_event_study(event_names=["large_down_day", "vix_shock_up"],
                        start="2020-01-01", end="2024-06-03")
    assert a["event_count"] == b["event_count"]
    assert a["statistics"].to_dict() == b["statistics"].to_dict()
