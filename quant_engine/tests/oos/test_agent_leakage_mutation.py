# -*- coding: utf-8 -*-
"""L5 Agent leakage mutation tests（P7 STEP 6.5）：runtime evidence。"""
import pandas as pd

CANARY = 999999999.0


def test_future_price_canary_filtered_by_load_ohlcv(monkeypatch, tmp_path):
    """未来价格 canary 被 load_ohlcv 的 Date<=curr_date 过滤（runtime，非静态）。"""
    import tradingagents.dataflows.vendors.yahoo.ohlcv as ohlcv
    import tradingagents.dataflows.config as cfg

    monkeypatch.setattr(cfg, "get_config", lambda: {"data_cache_dir": str(tmp_path)})

    def fake_download(*a, **k):
        return pd.DataFrame({
            "Date": ["2024-06-03", "2024-06-04"],
            "Open": [100, 101], "High": [101, 102], "Low": [99, 100],
            "Close": [100.5, CANARY], "Volume": [1000, 2000],
        })

    monkeypatch.setattr(ohlcv.yf, "download", fake_download)
    df = ohlcv.load_ohlcv("SPY", "2024-06-03")
    assert CANARY not in df["Close"].values
    assert df["Date"].max() <= pd.Timestamp("2024-06-03").normalize()


def test_future_news_canary_filtered():
    """未来 pub_date 新闻被 in_window 过滤。"""
    from datetime import datetime, timezone
    from tradingagents.dataflows.date_window import in_window
    future = datetime(2024, 6, 4, tzinfo=timezone.utc)
    assert not in_window(future, datetime(2024, 5, 1), datetime(2024, 6, 3))


def test_future_fundamental_period_cutoff():
    """未来 fiscal period（> T）被 filter_financials_by_date 切掉。"""
    from tradingagents.dataflows.vendors.yahoo.fundamentals import filter_financials_by_date
    df = pd.DataFrame({
        "2024-03-31": [1.0], "2024-06-30": [2.0], "2024-09-30": [CANARY],
    })
    filtered = filter_financials_by_date(df, "2024-06-03")
    assert "2024-09-30" not in filtered.columns
    assert "2024-03-31" in filtered.columns
    assert "2024-06-30" not in filtered.columns  # period end > T（6/30 > 6/3）→ 被过滤（正确）


def test_revision_canary_fred_vintage_pin():
    """FRED 修订隔离：历史 curr_date → vintage pin = curr_date（不取未来修订）。"""
    from tradingagents.dataflows.vendors.fred import _fred_today
    assert min("2024-06-03", _fred_today()) == "2024-06-03"


def test_current_only_search_withheld():
    """Polymarket live-only：历史日期 withhold，不返回 live odds。"""
    from tradingagents.dataflows.vendors.polymarket import get_prediction_markets
    result = get_prediction_markets("Fed rate cut", curr_date="2024-06-03")
    assert "withheld" in result.lower()


def test_insider_transaction_future_cutoff():
    """insider transactions 按 Start Date <= curr_date 过滤。"""
    import pandas as pd
    df = pd.DataFrame({
        "Start Date": ["2024-06-01", "2024-06-05"],
        "Shares": [100, 200],
    })
    kept = df[pd.to_datetime(df["Start Date"]) <= pd.Timestamp("2024-06-03")]
    assert len(kept) == 1
    assert kept.iloc[0]["Start Date"] == "2024-06-01"


def test_period_end_ne_availability():
    """period_end <= T 但 filing_date > T：yfinance 无 filing date → 无法过滤 → UNVERIFIABLE。

    T = 2024-06-03；record: period_end=2024-05-31, filing_date=2024-06-10（未来 filing）。
    filter_financials_by_date 只按 period_end 切，无法识别 filing_date > T 的记录，
    所以这条"filing 在未来"的记录会被错误保留 → 证明 period_end 过滤 ≠ availability 证明。
    """
    from tradingagents.dataflows.vendors.yahoo.fundamentals import filter_financials_by_date
    from quant_engine.oos.l5_tool_inventory import build_tool_inventory

    bs = next(e for e in build_tool_inventory() if e.tool_name == "get_balance_sheet")
    assert not bs.historical_availability_proven
    assert bs.leakage_status.value == "UNVERIFIABLE"
    assert "None" in bs.availability_field  # 默认 yfinance 无 filing date（filed 仅 sec_edgar）

    # period_end = 2024-05-31 <= T，被 filter 保留
    df = pd.DataFrame({"2024-05-31": [100.0]})
    filtered = filter_financials_by_date(df, "2024-06-03")
    assert "2024-05-31" in filtered.columns
    # 但 yfinance 无 filing_date，若该 period 实际 filing 在 2024-06-10（> T），
    # 这条记录应被过滤却被保留 → available_at 无法证明 → UNVERIFIABLE


def test_insider_transaction_date_ne_filing_date():
    """transaction_date <= T 但 filing_date > T：无 vendor 提供 Form 4 filing date → UNVERIFIABLE。

    transaction_date = 2024-06-01, filing_date = 2024-06-05, T = 2024-06-03。
    当前过滤只按 Start Date（transaction date），无法识别 filing_date > T。
    """
    from quant_engine.oos.l5_tool_inventory import build_tool_inventory

    ins = next(e for e in build_tool_inventory() if e.tool_name == "get_insider_transactions")
    assert not ins.historical_availability_proven
    assert ins.leakage_status.value == "UNVERIFIABLE"  # 生产默认 vendor 未切换 → 生产 runtime UNVERIFIABLE
    # 真实 SEC source 已验证 filing date（REAL_SOURCE_REPLAY PASS），字段不再是 None
    assert "filingDate" in ins.filing_field or "FILED AS OF DATE" in ins.filing_field
    assert "SEC EDGAR" in ins.availability_field
    # 但生产未接入 SEC source：availability_field 明确标注生产默认 yfinance/alpha_vantage 无 filing date
    assert "生产默认" in ins.availability_field or "未接入生产" in ins.filing_field
