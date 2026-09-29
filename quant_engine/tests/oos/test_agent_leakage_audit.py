# -*- coding: utf-8 -*-
"""L5 Agent Leakage Audit 单元测试（P7 STEP 6.5）。"""
from tradingagents.dataflows.date_window import (
    as_of, as_of_window, withhold_live_profile, in_window, get_current_date,
)

from quant_engine.oos.l5_models import ToolLeakageStatus
from quant_engine.oos.l5_tool_inventory import build_tool_inventory
from quant_engine.oos.l5_audit import audit_l5


def test_l5_audit_blocked():
    r = audit_l5("p1", "2024-06-03T23:59:59")
    assert r.status == "BLOCKED"
    assert len(r.tool_inventory) == 12
    assert len(r.blocked_tools) == 4
    assert r.llm_parametric_knowledge == "OUT_OF_SCOPE"


def test_inventory_all_have_cutoff():
    inv = build_tool_inventory()
    for e in inv:
        # 每个 tool 都有 trade_date 输入控制（无 NO_CUTOFF / LEAKAGE_RISK / CURRENT_ONLY）
        assert e.leakage_status != ToolLeakageStatus.LEAKAGE_RISK
        assert e.leakage_status != ToolLeakageStatus.CURRENT_ONLY


def test_unverifiable_recorded_honestly():
    r = audit_l5("p1", "2024-06-03T23:59:59")
    # 4 个 statement/insider tool 是 UNVERIFIABLE（fail-closed，不能默认 SAFE）
    names = [b for b in r.blocked_tools]
    assert "get_balance_sheet" in names
    assert "get_cashflow" in names
    assert "get_income_statement" in names
    assert "get_insider_transactions" in names
    assert len(r.blocked_tools) == 4
    # 4 条 UNVERIFIABLE_AVAILABILITY violation
    unv = [v for v in r.violations
           if v.violation_type.value == "UNVERIFIABLE_AVAILABILITY"]
    assert len(unv) == 4


def test_audit_id_deterministic():
    r1 = audit_l5("p1", "2024-06-03T23:59:59")
    r2 = audit_l5("p1", "2024-06-03T23:59:59")
    assert r1.audit_id == r2.audit_id
    assert len(r1.audit_id) == 64


# ── cutoff propagation runtime evidence ──
def test_as_of_clamps_future_request():
    # model 请求未来日期 → 钳制到 trade_date
    assert as_of("2024-06-10", "2024-06-03") == "2024-06-03"


def test_as_of_allows_past_request():
    assert as_of("2024-06-01", "2024-06-03") == "2024-06-01"


def test_as_of_empty_trade_date_passthrough():
    assert as_of("2024-06-10", "") == "2024-06-10"


def test_as_of_window_clamps_end():
    start, end = as_of_window("2024-05-01", "2024-06-10", "2024-06-03")
    assert end == "2024-06-03"


def test_as_of_window_moves_fully_future_window():
    # 窗口整体在未来 → 移到 trade_date 结束
    start, end = as_of_window("2024-06-05", "2024-06-10", "2024-06-03")
    assert end == "2024-06-03"


def test_withhold_live_profile_historical():
    result = withhold_live_profile("2020-03-16", "SPY")
    assert result is not None
    assert "withheld" in result.lower()


def test_withhold_live_profile_live():
    result = withhold_live_profile(get_current_date(), "SPY")
    assert result is None


def test_in_window_filters_future_publication():
    from datetime import datetime, timezone
    future = datetime(2024, 6, 4, tzinfo=timezone.utc)
    assert not in_window(future, datetime(2024, 5, 1), datetime(2024, 6, 3))
