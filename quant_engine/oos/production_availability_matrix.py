# -*- coding: utf-8 -*-
"""Production Availability Path Matrix（P7 STEP 6.5D 第 2 节）。

审计实际 runtime path：Agent → Tool → dataflow → configured vendor → raw response → availability adapter。

三层区分（用户第 15 节）：
1. source capability（6.5C-1 已证明 SEC EDGAR filed/filingDate = PIT_SAFE 能力）
2. configured production path（本阶段审计：default_config + router VENDOR_METHODS）
3. actual runtime observation（本阶段验证：runtime 返回数据 + availability evidence）
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductionPathEntry:
    tool_name: str
    agent: str
    configured_vendor: str
    actual_runtime_provider: str
    candidate_pit_safe_provider: str | None
    availability_source_field: str | None
    available_at_semantics: str
    runtime_reachable: bool          # 本环境能否真实网络调用该 provider
    runtime_pit_status: str          # PIT_SAFE / UNVERIFIABLE / UNSAFE / NOT_SUPPORTED
    fallback_path: str


def build_production_matrix() -> list[ProductionPathEntry]:
    """4 个 L5 blocker 的 production path 审计结论（runtime 代码审查）。"""
    return [
        ProductionPathEntry(
            tool_name="get_balance_sheet",
            agent="fundamentals_analyst",
            configured_vendor="yfinance",
            actual_runtime_provider="get_yfinance_balance_sheet → filter_financials_by_date（period_end 过滤，无 filing date）",
            candidate_pit_safe_provider="sec_edgar（get_sec_edgar_balance_sheet → _as_of 按 fact['filed']<=curr_date 过滤）",
            availability_source_field="None（yfinance）；filed（sec_edgar）",
            available_at_semantics="yfinance 仅 period_end，无 filing date → available_at 无法建立；sec_edgar filed=提交日=PIT_SAFE",
            runtime_reachable=False,  # sec.gov TLS 阻断，sec_edgar 无法真实调用
            runtime_pit_status="UNVERIFIABLE",
            fallback_path="显式 chain，无 silent fallback；sec_edgar 失败→VendorRateLimitError→DATA_UNAVAILABLE sentinel",
        ),
        ProductionPathEntry(
            tool_name="get_cashflow",
            agent="fundamentals_analyst",
            configured_vendor="yfinance",
            actual_runtime_provider="get_yfinance_cashflow → filter_financials_by_date（period_end 过滤）",
            candidate_pit_safe_provider="sec_edgar（get_sec_edgar_cashflow → _as_of filed<=curr_date）",
            availability_source_field="None（yfinance）；filed（sec_edgar）",
            available_at_semantics="yfinance 仅 period_end 无 filing date → UNVERIFIABLE；sec_edgar filed=PIT_SAFE",
            runtime_reachable=False,
            runtime_pit_status="UNVERIFIABLE",
            fallback_path="显式 chain，无 silent fallback；DATA_UNAVAILABLE sentinel",
        ),
        ProductionPathEntry(
            tool_name="get_income_statement",
            agent="fundamentals_analyst",
            configured_vendor="yfinance",
            actual_runtime_provider="get_yfinance_income_statement → filter_financials_by_date（period_end 过滤）",
            candidate_pit_safe_provider="sec_edgar（get_sec_edgar_income_statement → _as_of filed<=curr_date）",
            availability_source_field="None（yfinance）；filed（sec_edgar）",
            available_at_semantics="yfinance 仅 period_end 无 filing date → UNVERIFIABLE；sec_edgar filed=PIT_SAFE",
            runtime_reachable=False,
            runtime_pit_status="UNVERIFIABLE",
            fallback_path="显式 chain，无 silent fallback；DATA_UNAVAILABLE sentinel",
        ),
        ProductionPathEntry(
            tool_name="get_insider_transactions",
            agent="fundamentals_analyst",
            configured_vendor="yfinance",
            actual_runtime_provider="get_yfinance_insider_transactions → Start Date（transaction date）过滤",
            candidate_pit_safe_provider="SEC EDGAR submissions（filingDate，6.5C-1 已验证）——但 router 未绑定 insider 的 sec_edgar 实现",
            availability_source_field="None（yfinance）；filingDate / FILED AS OF DATE（SEC EDGAR，未接入生产）",
            available_at_semantics="yfinance transaction_date != filing_date → UNVERIFIABLE；SEC EDGAR filingDate=提交日=PIT_SAFE（未接入）",
            runtime_reachable=False,
            runtime_pit_status="UNVERIFIABLE",
            fallback_path="显式 chain，无 silent fallback；yfinance/alpha_vantage 均无 filing date",
        ),
    ]


def blocker_summary() -> dict:
    """4 个 blocker 的三层状态汇总（供 L5 聚合 + 报告用）。"""
    entries = build_production_matrix()
    return {
        "blockers": [
            {
                "tool": e.tool_name,
                "configured_vendor": e.configured_vendor,
                "candidate_pit_safe": e.candidate_pit_safe_provider,
                "runtime_reachable": e.runtime_reachable,
                "runtime_pit_status": e.runtime_pit_status,
            }
            for e in entries
        ],
        "all_pit_safe": all(e.runtime_pit_status == "PIT_SAFE" for e in entries),
        "any_unverifiable": any(e.runtime_pit_status == "UNVERIFIABLE" for e in entries),
    }
