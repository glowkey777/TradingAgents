# -*- coding: utf-8 -*-
"""Production No-Fallback 测试（P7 STEP 6.5E 第 5/13/16 节）。

验证：无 silent fallback、无 current snapshot fallback、unsupported filer fail-closed。
"""
import pytest

from tradingagents.dataflows.errors import NoMarketDataError, VendorRateLimitError


def test_sec_form4_unsupported_filer_fail_closed(monkeypatch):
    """非 US filer → NoMarketDataError，不 fallback yfinance。"""
    from tradingagents.dataflows.vendors import sec_form4
    monkeypatch.setattr(sec_form4, "cik_for", lambda ticker: None)
    with pytest.raises(NoMarketDataError):
        sec_form4.get_insider_transactions("SOMENONUSFILER", "2024-06-03")


def test_sec_form4_network_failure_typed_error(monkeypatch):
    """SEC 网络失败 → VendorRateLimitError（typed），不 silent 换 vendor。"""
    from tradingagents.dataflows.vendors import sec_form4
    monkeypatch.setattr(sec_form4, "cik_for", lambda ticker: "0001341439")
    monkeypatch.setattr(
        sec_form4, "_form4_filings_by_cik",
        lambda cik: (_ for _ in ()).throw(VendorRateLimitError("SEC unreachable")),
    )
    with pytest.raises(VendorRateLimitError):
        sec_form4.get_insider_transactions("ORCL", "2024-06-03")


def test_no_current_snapshot_fallback():
    """as_of=2024-06-26 时，filing_date=2024-06-27 的 filing 不可见（不返回未来 snapshot）。"""
    from quant_engine.oos.sec_form4_adapter import sec_form4_insider_transactions
    # as_of = 2024-06-26（filing_date 06-27 在未来）→ 无可见记录
    result = sec_form4_insider_transactions("2024-06-26 23:59:59")
    assert "NO_DATA_AVAILABLE" in result  # 未来 filing 不可见，不返回 snapshot


def test_current_snapshot_visible_after_filing():
    """as_of=2024-06-27（>= filing_date）→ 记录可见。"""
    from quant_engine.oos.sec_form4_adapter import sec_form4_insider_transactions
    result = sec_form4_insider_transactions("2024-06-27 23:59:59")
    assert "NO_DATA_AVAILABLE" not in result
    assert "Screven Edward" in result


def test_router_no_silent_fallback_to_yfinance():
    """router：配置 sec_form4（唯一）时不 silent fallback 到 yfinance。"""
    from tradingagents.dataflows import router as router_mod
    orig = router_mod.get_vendor
    router_mod.get_vendor = lambda category, method=None: "sec_form4"
    try:
        # sec_form4 对非 US filer 抛 NoMarketDataError，router 不应 fallback yfinance
        from tradingagents.dataflows.router import route_to_vendor
        result = route_to_vendor("get_insider_transactions", "SOMENONUSFILER", "2024-06-03")
        # fail-closed：返回 sentinel 或 raise，绝不返回 yfinance 数据
        assert "NO_DATA" in result or "UNAVAILABLE" in result
    finally:
        router_mod.get_vendor = orig
