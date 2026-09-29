# -*- coding: utf-8 -*-
"""Vendor Config Provenance 测试（P7 STEP 6.5E 第 8/9 节）。

验证 vendor_config_version 记录 old→new 绑定，且不重写历史 provenance。
"""
from tradingagents.dataflows.config import get_config


def test_vendor_config_version_present():
    """vendor_config_version 记录 6.5E-v1 绑定。"""
    cfg = get_config()
    v = cfg.get("vendor_config_version", {})
    assert v["version"] == "6.5E-v1"
    assert v["statement_vendors"] == {"old": "yfinance", "new": "sec_edgar"}
    assert v["insider_transactions"] == {"old": "yfinance/alpha_vantage", "new": "sec_form4"}


def test_vendor_config_records_coverage_and_failure():
    """记录 coverage / unsupported_symbols / failure_behavior / fallback_behavior。"""
    v = get_config().get("vendor_config_version", {})
    assert "US SEC filers" in v["coverage"]
    assert "NoMarketDataError" in v["unsupported_symbols"]
    assert "no silent fallback" in v["failure_behavior"]
    assert "PIT safety" in v["fallback_behavior"]


def test_config_current_distinct_from_historical_provenance():
    """CONFIGURATION_CURRENT 与 HISTORICAL_PREDICTION_PROVENANCE 分离。"""
    v = get_config().get("vendor_config_version", {})
    # 配置版本只记录当前切换，不包含历史预测 provenance 重写字段
    assert "historical_prediction_rewrite" not in v
    assert v["statement_vendors"]["old"] == "yfinance"  # 明确记录 old，不是静默覆盖


def test_statement_vendor_bound_sec_edgar():
    """3 个 statement 已切 sec_edgar（PIT-safe）。"""
    tv = get_config()["tool_vendors"]
    assert tv["get_balance_sheet"] == "sec_edgar"
    assert tv["get_cashflow"] == "sec_edgar"
    assert tv["get_income_statement"] == "sec_edgar"


def test_insider_bound_sec_form4():
    """生产 insider 已切 sec_form4（PIT-safe）。"""
    assert get_config()["tool_vendors"]["get_insider_transactions"] == "sec_form4"
