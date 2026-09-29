# -*- coding: utf-8 -*-
"""yfinance Loader：宏观数据（VIX/US5Y/US10Y/DXY/WTI），非 canonical price（SPY 价格以 OpenD 为准）。"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf

from ..config import YFINANCE_SYMBOLS, DATASET_VERSIONS, TIMEZONE
from ..models import MarketDataPoint

START = "2013-01-01"


class YFinanceLoader:
    def _fetch(self, ticker: str) -> pd.Series:
        df = yf.download(ticker, start=START, auto_adjust=True, progress=False)
        if df is None or df.empty:
            raise ValueError(f"empty: {ticker}")
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close

    def fetch_macro(self) -> list[MarketDataPoint]:
        points = []
        for field, (ticker, unit) in YFINANCE_SYMBOLS.items():
            if field == "spy_close":
                continue  # SPY 价格 canonical 用 OpenD，yfinance 只作 cross-check
            try:
                series = self._fetch(ticker)
            except Exception as exc:
                print(f"[skip] {field} ({ticker}): {exc}")
                continue
            for ts, value in series.items():
                if pd.isna(value):
                    continue
                avail = ts.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                points.append(MarketDataPoint(
                    timestamp=ts, symbol=field, field=field, value=float(value),
                    source="yfinance", observation_time=avail, available_at=avail,
                    frequency="daily", timezone=TIMEZONE, unit=unit,
                    price_basis="unadjusted", adjustment="NONE",
                    dataset_version=DATASET_VERSIONS["macro_daily"]))
        return points
