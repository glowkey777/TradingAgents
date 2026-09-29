# -*- coding: utf-8 -*-
"""L5 Tool Inventory（P7 STEP 6.5）。

基于对 tradingagents/agents/tools.py + dataflows/vendors/* 的逐文件 runtime 代码审查，
记录每个 agent tool 的 cutoff 机制与 PIT 状态。这是"清单"，PIT 证明由 mutation tests 提供。
"""
from __future__ import annotations

from .l5_models import ToolInventoryEntry, ToolLeakageStatus


def build_tool_inventory() -> list[ToolInventoryEntry]:
    """12 个 agent tool 的 L5 清单（runtime 代码审查结论）。"""
    return [
        ToolInventoryEntry(
            tool_name="get_stock_data",
            data_source="yfinance / alpha_vantage",
            input_date_controls="trade_date(InjectedState) + as_of_window",
            historical_cutoff_mechanism="yfinance history end 钳制到 trade_date + _assert_ohlcv_not_stale 拒绝 stale",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="tools.py:34 as_of_window；market.py:38-39 end_inclusive；ohlcv.py _assert_ohlcv_not_stale",
        ),
        ToolInventoryEntry(
            tool_name="get_indicators",
            data_source="yfinance / alpha_vantage",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="load_ohlcv 内 Date <= curr_date 过滤",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="tools.py:59 as_of；market.py:160 load_ohlcv(curr_date)；ohlcv.py:261 Date<=curr_date",
        ),
        ToolInventoryEntry(
            tool_name="get_verified_market_snapshot",
            data_source="yfinance (本地缓存)",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="_verified_rows 重新应用 Date <= curr_date（防御性二次过滤）",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="tools.py:86 as_of；snapshot.py:44 df[Date<=curr_date]",
        ),
        ToolInventoryEntry(
            tool_name="get_fundamentals",
            data_source="yfinance / alpha_vantage",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="withhold_live_profile：历史日期 withhold 无 vintage 的 profile（Ticker.info/OVERVIEW）",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="fundamentals.py:31 withhold_live_profile；date_window.py:98-124",
        ),
        ToolInventoryEntry(
            tool_name="get_balance_sheet",
            data_source="yfinance(默认) / alpha_vantage / sec_edgar",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="filter_financials_by_date 按 fiscal period end <= curr_date 切（yfinance/AV）",
            availability_field="None（默认 yfinance/AV）；filed（仅 sec_edgar，默认未启用）",
            availability_semantics="默认 fundamental_data=yfinance 只按 period_end 切，无 filing date → available_at 无法建立",
            filing_field="filed（仅 sec_edgar vendor）",
            publication_field="None",
            revision_field="None",
            historical_availability_proven=False,
            pit_safe=False, leakage_status=ToolLeakageStatus.UNVERIFIABLE,
            evidence="default_config.py fundamental_data=yfinance；fundamentals.py filter_financials_by_date 无 filing date；sec_edgar.py fact['filed'] 有但默认不启用",
        ),
        ToolInventoryEntry(
            tool_name="get_cashflow",
            data_source="yfinance(默认) / alpha_vantage / sec_edgar",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="filter_financials_by_date 按 fiscal period end <= curr_date 切（无 filing date）",
            availability_field="None（默认 yfinance/AV）；filed（仅 sec_edgar）",
            availability_semantics="默认 yfinance 只按 period_end 切，无 filing date → available_at 无法建立",
            filing_field="filed（仅 sec_edgar vendor）",
            publication_field="None",
            revision_field="None",
            historical_availability_proven=False,
            pit_safe=False, leakage_status=ToolLeakageStatus.UNVERIFIABLE,
            evidence="filter_financials_by_date 无 filing date；period_end <= T ≠ available_at <= T",
        ),
        ToolInventoryEntry(
            tool_name="get_income_statement",
            data_source="yfinance(默认) / alpha_vantage / sec_edgar",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="filter_financials_by_date 按 fiscal period end <= curr_date 切（无 filing date）",
            availability_field="None（默认 yfinance/AV）；filed（仅 sec_edgar）",
            availability_semantics="默认 yfinance 只按 period_end 切，无 filing date → available_at 无法建立",
            filing_field="filed（仅 sec_edgar vendor）",
            publication_field="None",
            revision_field="None",
            historical_availability_proven=False,
            pit_safe=False, leakage_status=ToolLeakageStatus.UNVERIFIABLE,
            evidence="filter_financials_by_date 无 filing date；period_end <= T ≠ available_at <= T",
        ),
        ToolInventoryEntry(
            tool_name="get_news",
            data_source="yfinance / alpha_vantage",
            input_date_controls="trade_date + as_of_window",
            historical_cutoff_mechanism="in_window(pub_date) half-open window 过滤 + coverage_gap 处理未观察窗口",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="tools.py:184 as_of_window；news.py:97 in_window；date_window.py:22-30",
        ),
        ToolInventoryEntry(
            tool_name="get_global_news",
            data_source="yfinance / alpha_vantage",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="in_window(pub_date) 过滤，flat article 也按 providerPublishTime 过滤",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="tools.py:209 as_of；news.py:167 in_window；news.py:44-58 flat 结构 epoch 解析",
        ),
        ToolInventoryEntry(
            tool_name="get_insider_transactions",
            data_source="yfinance / alpha_vantage（生产默认）",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="Start Date（transaction date）<= curr_date 过滤",
            availability_field="SEC EDGAR filingDate（REAL_SOURCE_REPLAY PASS：真实 Form 4 0001127602-24-019342 已验证 FILED AS OF DATE 语义）；生产默认 yfinance/alpha_vantage 无 filing date",
            availability_semantics="availability 能力已 RESOLVED（SEC EDGAR submissions/complete-submission header 提供 Form 4 filing date）；但生产默认 vendor 未切换，transaction_date <= T ≠ filing_date <= T → 生产 runtime available_at 仍无法建立",
            filing_field="filingDate / FILED AS OF DATE（仅 SEC EDGAR source，未接入生产）",
            publication_field="None",
            revision_field="None",
            historical_availability_proven=False,
            pit_safe=False, leakage_status=ToolLeakageStatus.UNVERIFIABLE,
            evidence="REAL_SOURCE_REPLAY PASS（real_sec_bridge + test_real_sec_replay 12 tests）；生产 fundamentals.py Start Date 过滤（transaction date），无 Form 4 filing date → 生产 runtime UNVERIFIABLE",
        ),
        ToolInventoryEntry(
            tool_name="get_macro_indicators",
            data_source="fred",
            input_date_controls="trade_date + as_of",
            historical_cutoff_mechanism="FRED realtime_start/end vintage pin（min(curr_date, fred_today)）——真正的 PIT 修订隔离",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="fred.py:192 pit=min(curr_date,_fred_today())；realtime vintage pin 防 revision leakage",
        ),
        ToolInventoryEntry(
            tool_name="get_prediction_markets",
            data_source="polymarket",
            input_date_controls="trade_date",
            historical_cutoff_mechanism="curr_date < today 时 withhold（Polymarket 无历史 vintage，历史日期不返回 live odds）",
            pit_safe=True, leakage_status=ToolLeakageStatus.PIT_SAFE,
            evidence="polymarket.py:86 curr_date<get_current_date() → withhold",
        ),
    ]
