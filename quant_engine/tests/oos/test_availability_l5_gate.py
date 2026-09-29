# -*- coding: utf-8 -*-
"""L5 Gate 集成（P7 STEP 6.5B 第 9/10 步：Reachability + L5 aggregation）。

最终 L5 只读取 availability evidence（用户第 14/15 节 fail-closed）。
"""
from quant_engine.oos.availability_source_matrix import build_source_matrix
from quant_engine.oos.availability_models import SourceStatus


# 4 个 statement/insider tool 被 fundamentals_analyst 显式绑定（reachable）。
# 证据：tradingagents/agents/analysts/fundamentals_analyst.py imports 这 4 个 tool。
REACHABLE_FUNDAMENTAL_TOOLS = {
    "get_balance_sheet", "get_cashflow",
    "get_income_statement", "get_insider_transactions",
}

# 默认配置（default_config.py）：fundamental_data = yfinance（无 filing date）。
DEFAULT_FUNDAMENTAL_VENDOR = "yfinance"


def l5_gate_from_matrix() -> str:
    """从 source capability matrix 计算 L5 最终状态。

    fail-closed（用户第 15 节）：
        FAIL    if 任一 PROVEN VIOLATION（未来信息进入）
        BLOCKED if 任一 reachable in-scope tool UNVERIFIABLE
        PASS    else
    """
    matrix = build_source_matrix()

    # reachable + in-scope 的 tool 行（排除已 PASS 的 news/fred/polymarket，聚焦 fundamentals/insider）
    reachable = [
        c for c in matrix
        if c.tool in REACHABLE_FUNDAMENTAL_TOOLS
    ]

    # 默认 vendor 的 capability 决定 statement 状态
    # 默认 yfinance（UNVERIFIABLE）；sec_edgar 可选但默认未启用
    default_edgar = any(
        c.vendor == "sec_edgar" and c.status == SourceStatus.PIT_SAFE
        for c in reachable
    )
    # insider 两个 vendor 都 UNVERIFIABLE
    insider_unverifiable = all(
        c.status == SourceStatus.UNVERIFIABLE
        for c in reachable if c.tool == "get_insider_transactions"
    )
    # statement 默认 vendor（yfinance）UNVERIFIABLE
    statement_default_unverifiable = all(
        c.status == SourceStatus.UNVERIFIABLE
        for c in reachable
        if c.tool != "get_insider_transactions" and c.vendor == DEFAULT_FUNDAMENTAL_VENDOR
    )

    proven_violation = any(
        c.status == SourceStatus.UNSAFE for c in reachable
    )

    if proven_violation:
        return "FAIL"
    # insider UNVERIFIABLE（reachable + in-scope）→ BLOCKED，即使 EDGAR 对 statement 可 PIT_SAFE
    if insider_unverifiable:
        return "BLOCKED"
    if statement_default_unverifiable:
        return "BLOCKED"
    return "PASS"


def test_reachable_tools_in_scope():
    """4 个 fundamentals/insider tool 是 reachable + in-scope（不能偷偷排除）。"""
    matrix = build_source_matrix()
    tools = {c.tool for c in matrix}
    assert REACHABLE_FUNDAMENTAL_TOOLS <= tools


def test_insider_unverifiable_reachable():
    """insider 两个 vendor 都 UNVERIFIABLE，且 reachable → L5 BLOCKED 的根源。"""
    matrix = build_source_matrix()
    insider = [c for c in matrix if c.tool == "get_insider_transactions"]
    assert len(insider) == 2
    assert all(c.status == SourceStatus.UNVERIFIABLE for c in insider)


def test_l5_gate_blocked():
    """最终 L5 = BLOCKED：SEC EDGAR PASS 不能覆盖 insider UNVERIFIABLE。"""
    assert l5_gate_from_matrix() == "BLOCKED"
