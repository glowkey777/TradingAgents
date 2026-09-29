# -*- coding: utf-8 -*-
"""Vendor Binding 测试（P7 STEP 6.5E 第 3/4/6 节）。

验证 configured vendor、router binding、binding matrix 一致性。
"""
from quant_engine.oos.production_vendor_binding_matrix import (
    build_binding_matrix, binding_summary,
)


def test_binding_matrix_four_tools():
    """4 个 blocker 全部有 old→new 绑定。"""
    entries = build_binding_matrix()
    tools = {e.tool for e in entries}
    assert tools == {
        "get_balance_sheet", "get_cashflow",
        "get_income_statement", "get_insider_transactions",
    }


def test_binding_matrix_fundamentals_to_sec_edgar():
    """fundamentals 3 tool old=yfinance new=sec_edgar，availability=filed。"""
    entries = build_binding_matrix()
    for tool in ("get_balance_sheet", "get_cashflow", "get_income_statement"):
        e = next(x for x in entries if x.tool == tool)
        assert e.old_vendor == "yfinance"
        assert e.new_vendor == "sec_edgar"
        assert e.availability_field == "filed"
        assert e.status == "PIT_SAFE"


def test_binding_matrix_insider_to_sec_form4():
    """insider old=yfinance/alpha_vantage new=sec_form4，availability=filingDate。"""
    entries = build_binding_matrix()
    e = next(x for x in entries if x.tool == "get_insider_transactions")
    assert e.old_vendor == "yfinance / alpha_vantage"
    assert e.new_vendor == "sec_form4"
    assert "filingDate" in e.availability_field or "FILED AS OF DATE" in e.availability_field
    assert e.status == "PIT_SAFE"


def test_binding_summary_all_bound_but_online_not_verified():
    """4 个 tool 全部绑定 PIT_SAFE，但 online runtime 仍 NOT_VERIFIED。"""
    s = binding_summary()
    assert s["all_bound"] is True
    assert s["online_runtime"] == "NOT_VERIFIED"


def test_configured_statement_vendor_sec_edgar():
    """3 个 statement 绑定 sec_edgar（tool_vendors 覆盖）。"""
    from tradingagents.dataflows.config import get_config
    tv = get_config()["tool_vendors"]
    assert tv["get_balance_sheet"] == "sec_edgar"
    assert tv["get_cashflow"] == "sec_edgar"
    assert tv["get_income_statement"] == "sec_edgar"


def test_configured_insider_sec_form4():
    """default_config tool_vendors 绑定 insider → sec_form4。"""
    from tradingagents.dataflows.config import get_config
    assert get_config()["tool_vendors"]["get_insider_transactions"] == "sec_form4"


def test_router_binding_sec_form4():
    """router VENDOR_METHODS 绑定 sec_form4 实现函数。"""
    from tradingagents.dataflows.router import VENDOR_METHODS
    assert "sec_form4" in VENDOR_METHODS["get_insider_transactions"]
    from tradingagents.dataflows.vendors.sec_form4 import get_insider_transactions
    assert VENDOR_METHODS["get_insider_transactions"]["sec_form4"] is get_insider_transactions
