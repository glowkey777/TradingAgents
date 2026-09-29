# -*- coding: utf-8 -*-
"""Production Fallback / Fail-closed 测试（P7 STEP 6.5D 第 4/5.3/13 节）。

验证：无 silent fallback、unsupported issuer fail-closed、typed error 而非静默降级。
"""
import pytest

from tradingagents.dataflows.errors import NoMarketDataError, VendorRateLimitError


def test_sec_edgar_fetch_failure_is_typed_error(monkeypatch):
    """sec_edgar 网络失败 → VendorRateLimitError（typed），不是 silent 返回 None。"""
    from tradingagents.dataflows.vendors import sec_edgar

    def boom(*a, **k):
        # 真实 TLS 阻断抛 requests.exceptions.SSLError（RequestException 子类）
        raise sec_edgar.requests.exceptions.ConnectionError("TLS handshake blocked")

    monkeypatch.setattr(sec_edgar.requests, "get", boom)
    with pytest.raises(VendorRateLimitError):
        sec_edgar._fetch_json("https://data.sec.gov/x")


def test_unsupported_issuer_fail_closed(monkeypatch):
    """非 US filer（cik_for → None）→ NoMarketDataError，不 fallback yfinance。"""
    from tradingagents.dataflows.vendors import sec_edgar

    monkeypatch.setattr(sec_edgar, "cik_for", lambda ticker: None)
    with pytest.raises(NoMarketDataError):
        sec_edgar._statement("balance_sheet", "SOMENONUSFILER", "quarterly", "2024-06-03", "Balance Sheet")


def test_router_no_silent_fallback_to_unconfigured_vendor():
    """router：显式配置的 vendor 列表就是 chain，不静默 fallback 到未配置 vendor。"""
    from tradingagents.dataflows.router import route_to_vendor

    # 用 monkeypatch 显式把 fundamental_data 配成 sec_edgar（唯一），
    # 验证不会静默 fallback 到 yfinance。这里直接验证 router 的显式 chain 逻辑：
    # 配置 "sec_edgar"（不在 VENDOR_METHODS[get_insider_transactions] 里）→ ValueError
    from tradingagents.dataflows import router as router_mod
    orig = router_mod.get_vendor
    router_mod.get_vendor = lambda category, method=None: "sec_edgar"
    try:
        with pytest.raises(ValueError):
            route_to_vendor("get_insider_transactions", "AAPL", "2024-06-03")
    finally:
        router_mod.get_vendor = orig


def test_data_unavailable_sentinel_not_fabrication():
    """router 全 vendor 不可用 → DATA_UNAVAILABLE sentinel（明确说不要 fabricate）。"""
    from tradingagents.dataflows.router import route_to_vendor
    from tradingagents.dataflows import router as router_mod

    # 让 get_insider_transactions 的两个 vendor 都抛 VendorRateLimitError
    orig_methods = router_mod.VENDOR_METHODS["get_insider_transactions"]
    def unavailable(*a, **k):
        raise VendorRateLimitError("throttled")
    router_mod.VENDOR_METHODS["get_insider_transactions"] = {
        "yfinance": unavailable, "alpha_vantage": unavailable,
    }
    orig_vendor = router_mod.get_vendor
    router_mod.get_vendor = lambda category, method=None: "yfinance,alpha_vantage"
    try:
        result = route_to_vendor("get_insider_transactions", "AAPL", "2024-06-03")
        assert "DATA_UNAVAILABLE" in result
        assert "fabricate" in result or "unavailable" in result.lower()
    finally:
        router_mod.VENDOR_METHODS["get_insider_transactions"] = orig_methods
        router_mod.get_vendor = orig_vendor
