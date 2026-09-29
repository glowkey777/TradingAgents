# -*- coding: utf-8 -*-
"""Production Availability Path 测试（P7 STEP 6.5D）。

验证 4 个 blocker 的 production path：configured vendor、runtime provider、
SEC EDGAR filed PIT 过滤语义（source capability 已 6.5C-1 证明，此处验证 configured path）。
"""
import pytest

from quant_engine.oos.production_availability_matrix import (
    build_production_matrix, blocker_summary,
)


def test_configured_statement_vendor_is_sec_edgar():
    """3 个 statement 用 tool_vendors 覆盖 sec_edgar（fundamental_data 类别仍 yfinance 供 get_fundamentals）。"""
    from tradingagents.dataflows.config import get_config
    cfg = get_config()
    tv = cfg.get("tool_vendors", {})
    assert tv["get_balance_sheet"] == "sec_edgar"
    assert tv["get_cashflow"] == "sec_edgar"
    assert tv["get_income_statement"] == "sec_edgar"


def test_actual_runtime_provider_binding():
    """router VENDOR_METHODS：insider 现在有 sec_form4，statement 有 sec_edgar。"""
    from tradingagents.dataflows.router import VENDOR_METHODS
    # statement 有 sec_edgar 实现（candidate PIT_SAFE）
    assert "sec_edgar" in VENDOR_METHODS["get_balance_sheet"]
    assert "sec_edgar" in VENDOR_METHODS["get_cashflow"]
    assert "sec_edgar" in VENDOR_METHODS["get_income_statement"]
    # insider 现在绑定 sec_form4（6.5E）
    assert "sec_form4" in VENDOR_METHODS["get_insider_transactions"]


def test_production_matrix_blockers_all_unverifiable():
    """4 个 blocker 生产 runtime 均 UNVERIFIABLE（默认 yfinance，sec.gov 不可达）。"""
    summary = blocker_summary()
    assert len(summary["blockers"]) == 4
    assert all(b["runtime_pit_status"] == "UNVERIFIABLE" for b in summary["blockers"])
    assert summary["any_unverifiable"] is True
    assert summary["all_pit_safe"] is False


def test_sec_edgar_filed_future_rejection():
    """sec_edgar _as_of：filed > curr_date 的 fact 被过滤（future filing rejection）。"""
    from tradingagents.dataflows.vendors.sec_edgar import _as_of
    facts = {
        "Assets": {
            "units": {
                "USD": [
                    # period end 2024-03-31，filed 2024-06-10（> T=2024-06-03）→ 未来 filing
                    {"filed": "2024-06-10", "end": "2024-03-31", "val": 200.0, "form": "10-Q"},
                ]
            }
        }
    }
    values, _ = _as_of(facts, ("Assets",), "2024-06-03", (60, 115))
    assert "2024-03-31" not in values  # filed 在未来 → 被过滤


def test_sec_edgar_filed_legitimate_retention():
    """sec_edgar _as_of：filed <= curr_date 的 fact 被保留（legitimate retention）。"""
    from tradingagents.dataflows.vendors.sec_edgar import _as_of
    facts = {
        "Assets": {
            "units": {
                "USD": [
                    {"filed": "2024-05-15", "end": "2024-03-31", "val": 100.0, "form": "10-Q"},
                ]
            }
        }
    }
    values, _ = _as_of(facts, ("Assets",), "2024-06-03", (60, 115))
    assert values["2024-03-31"] == 100.0  # filed <= T → 保留


def test_sec_edgar_revision_vintage():
    """amendment 取最新 filed（revision vintage：filed 更晚的覆盖）。"""
    from tradingagents.dataflows.vendors.sec_edgar import _as_of
    facts = {
        "Assets": {
            "units": {
                "USD": [
                    {"filed": "2024-05-15", "end": "2024-03-31", "val": 100.0, "form": "10-Q"},
                    # amendment filed 2024-05-20（<= T）→ 取这个（restated 值）
                    {"filed": "2024-05-20", "end": "2024-03-31", "val": 95.0, "form": "10-Q/A"},
                ]
            }
        }
    }
    values, _ = _as_of(facts, ("Assets",), "2024-06-03", (60, 115))
    assert values["2024-03-31"] == 95.0  # 取最新 filed 的 restated 值
