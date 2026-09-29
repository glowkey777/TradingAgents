# -*- coding: utf-8 -*-
"""L5 Agent leakage replay harness（P7 STEP 6.5）：trade_date 全局 cutoff 传播。"""
import inspect

from tradingagents.graph.propagation import Propagator
import tradingagents.agents.tools as tools


def test_trade_date_propagation_to_state():
    p = Propagator()
    state = p.create_initial_state("SPY", "2024-06-03")
    assert state["trade_date"] == "2024-06-03"


def test_two_anchor_trade_date():
    p = Propagator()
    s1 = p.create_initial_state("SPY", "2020-03-16")
    s2 = p.create_initial_state("SPY", "2024-06-03")
    assert s1["trade_date"] == "2020-03-16"
    assert s2["trade_date"] == "2024-06-03"


def test_all_dated_tools_have_trade_date_injection():
    """每个 dated tool 都声明 trade_date: InjectedState，LangGraph 自动注入全局 cutoff。"""
    dated = ["get_stock_data", "get_indicators", "get_verified_market_snapshot",
             "get_fundamentals", "get_balance_sheet", "get_cashflow",
             "get_income_statement", "get_news", "get_global_news",
             "get_insider_transactions", "get_macro_indicators", "get_prediction_markets"]
    for name in dated:
        fn = getattr(tools, name, None)
        assert fn is not None, f"{name} missing"
        sig = inspect.signature(fn.func if hasattr(fn, "func") else fn)
        assert "trade_date" in sig.parameters, f"{name} 缺少 trade_date 注入"
