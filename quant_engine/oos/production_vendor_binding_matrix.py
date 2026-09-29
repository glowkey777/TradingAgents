# -*- coding: utf-8 -*-
"""Production Vendor Binding Matrix（P7 STEP 6.5E 第 3 节）。

记录 4 个 blocker 的 old→new vendor 绑定、adapter、availability 语义、replay 能力。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VendorBindingEntry:
    tool: str
    old_vendor: str
    new_vendor: str
    adapter: str
    availability_field: str
    availability_semantics: str
    runtime_reachable: bool          # sec.gov 网络可达（本环境 False）
    offline_replay_supported: bool   # 真实 artifact 离线 replay
    online_runtime_supported: bool   # 线上真实 runtime（NOT_VERIFIED）
    coverage: str
    fallback: str
    config_version: str
    status: str                       # PIT_SAFE / UNVERIFIABLE / NOT_VERIFIED


def build_binding_matrix() -> list[VendorBindingEntry]:
    """4 个 blocker 的 vendor 绑定矩阵。"""
    return [
        VendorBindingEntry(
            tool="get_balance_sheet",
            old_vendor="yfinance",
            new_vendor="sec_edgar",
            adapter="get_sec_edgar_balance_sheet → _as_of（fact['filed']<=curr_date）",
            availability_field="filed",
            availability_semantics="filed = Form 提交日 = available_at；amendment 取最新 filed（vintage）",
            runtime_reachable=False,
            offline_replay_supported=True,
            online_runtime_supported=False,
            coverage="US SEC filers only（cik_for 查 company_tickers）",
            fallback="无 silent fallback；非 US filer → NoMarketDataError；网络失败 → VendorRateLimitError → DATA_UNAVAILABLE",
            config_version="6.5E-v1",
            status="PIT_SAFE",  # 绑定后 capability 层 PIT_SAFE（online runtime 仍 NOT_VERIFIED）
        ),
        VendorBindingEntry(
            tool="get_cashflow",
            old_vendor="yfinance",
            new_vendor="sec_edgar",
            adapter="get_sec_edgar_cashflow → _as_of（filed<=curr_date）",
            availability_field="filed",
            availability_semantics="filed = 提交日 = available_at；revision 由 filed vintage 承担",
            runtime_reachable=False,
            offline_replay_supported=True,
            online_runtime_supported=False,
            coverage="US SEC filers only",
            fallback="无 silent fallback；typed failure",
            config_version="6.5E-v1",
            status="PIT_SAFE",
        ),
        VendorBindingEntry(
            tool="get_income_statement",
            old_vendor="yfinance",
            new_vendor="sec_edgar",
            adapter="get_sec_edgar_income_statement → _as_of（filed<=curr_date）",
            availability_field="filed",
            availability_semantics="filed = 提交日 = available_at；revision 由 filed vintage 承担",
            runtime_reachable=False,
            offline_replay_supported=True,
            online_runtime_supported=False,
            coverage="US SEC filers only",
            fallback="无 silent fallback；typed failure",
            config_version="6.5E-v1",
            status="PIT_SAFE",
        ),
        VendorBindingEntry(
            tool="get_insider_transactions",
            old_vendor="yfinance / alpha_vantage",
            new_vendor="sec_form4",
            adapter="get_sec_form4_insider_transactions（6.5C-1 real parser）→ filing_date → available_at",
            availability_field="filingDate / FILED AS OF DATE",
            availability_semantics="filing_date = Form 4 提交日 = available_at；transaction_date ≠ available_at",
            runtime_reachable=False,
            offline_replay_supported=True,
            online_runtime_supported=False,
            coverage="US SEC filers with Form 4 filings",
            fallback="无 silent fallback；非 US filer / 无 Form 4 → typed failure",
            config_version="6.5E-v1",
            status="PIT_SAFE",  # 绑定后 capability 层 PIT_SAFE（online runtime 仍 NOT_VERIFIED）
        ),
    ]


def binding_summary() -> dict:
    entries = build_binding_matrix()
    return {
        "tools": [
            {"tool": e.tool, "old": e.old_vendor, "new": e.new_vendor, "status": e.status}
            for e in entries
        ],
        "all_bound": all(e.status == "PIT_SAFE" for e in entries),
        "online_runtime": "NOT_VERIFIED" if all(not e.online_runtime_supported for e in entries) else "MIXED",
    }
