# -*- coding: utf-8 -*-
"""L5 Agent leakage audit independence tests（P7 STEP 6.5）。"""
from datetime import datetime, timezone

from quant_engine.oos.l5_audit import audit_l5
from quant_engine.oos.l5_tool_inventory import build_tool_inventory


def test_audit_not_relying_on_agent_claim():
    """audit 基于 tool inventory 的 cutoff 机制（代码审查证据），不依赖 agent 自声称。"""
    r = audit_l5("p1", "2024-06-03T23:59:59")
    assert r.status == "BLOCKED"
    # 无 agent self-claim 字段（不信任 agent 说"我只用了历史信息"）
    d = r.model_dump()
    assert "agent_claim" not in d
    assert "self_report" not in d


def test_valid_historical_observation_not_false_positive():
    """negative control：合法历史观察不被误判为 leakage。"""
    from tradingagents.dataflows.date_window import in_window
    past = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert in_window(past, datetime(2024, 5, 1), datetime(2024, 6, 3))


def test_future_observation_detected():
    """positive control：未来观察被正确识别为 out-of-window。"""
    from tradingagents.dataflows.date_window import in_window
    future = datetime(2024, 6, 4, tzinfo=timezone.utc)
    assert not in_window(future, datetime(2024, 5, 1), datetime(2024, 6, 3))


def test_pit_safe_tools_outnumber_unverifiable():
    """PIT_SAFE tool 数量 > UNVERIFIABLE（8 vs 4），但 UNVERIFIABLE 仍导致 BLOCKED。"""
    inv = build_tool_inventory()
    pit_safe = [e for e in inv if e.leakage_status.value == "PIT_SAFE"]
    unverifiable = [e for e in inv if e.leakage_status.value == "UNVERIFIABLE"]
    assert len(pit_safe) == 8
    assert len(unverifiable) == 4
    assert len(inv) == 12
