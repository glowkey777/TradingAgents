# -*- coding: utf-8 -*-
"""本地 CSV Loader：历史补充 / 交叉验证，**不是 canonical price**。

spy_daily CSV 是复权价（yfinance auto_adjust），必须标 price_basis=adjusted，
禁止与 OpenD 未复权价混算。
"""
from __future__ import annotations

import pandas as pd

from ..config import DATASET_VERSIONS, TIMEZONE
from ..models import MarketDataPoint

SPY_DAILY = r"F:\Youtube\stock\spy_daily_2013_2026.csv"
SPY_MACRO = r"F:\Youtube\stock\spy_macro_2013_2026.csv"


def load_spy_daily_csv(path: str = SPY_DAILY) -> list[MarketDataPoint]:
    """SPY 日线 CSV → MarketDataPoint（复权价，cross-check 用）。"""
    df = pd.read_csv(path, parse_dates=["Date"])
    points = []
    for _, row in df.iterrows():
        ts = pd.Timestamp(row["Date"])
        avail = ts.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
        base = dict(symbol="SPY", source="csv", frequency="daily",
                    timezone=TIMEZONE, price_basis="adjusted", adjustment="DIVIDEND",
                    dataset_version=DATASET_VERSIONS["spy_daily"])
        for field in ("open", "high", "low", "close"):
            points.append(MarketDataPoint(
                timestamp=ts, field=field, value=float(row[field.capitalize()]),
                observation_time=avail, available_at=avail, **base))
        points.append(MarketDataPoint(
            timestamp=ts, field="volume", value=float(row["Volume"]),
            observation_time=avail, available_at=avail, **base))
    return points


def load_macro_csv(path: str = SPY_MACRO) -> list[MarketDataPoint]:
    """宏观宽表 CSV → MarketDataPoint（yfinance 源，cross-check 用）。"""
    df = pd.read_csv(path, index_col="date", parse_dates=["date"])
    fields = {"vix": ("VIX", "index"), "us5y": ("US5Y", "percent"),
              "us10y": ("US10Y", "percent"), "dxy": ("DXY", "index"), "wti": ("WTI", "usd")}
    points = []
    for col, (symbol, unit) in fields.items():
        for ts, value in df[col].items():
            if pd.isna(value):
                continue
            avail = ts.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
            points.append(MarketDataPoint(
                timestamp=ts, symbol=symbol, field=col, value=float(value),
                source="csv", observation_time=avail, available_at=avail,
                frequency="daily", timezone=TIMEZONE, unit=unit,
                price_basis="unadjusted", adjustment="NONE",
                dataset_version=DATASET_VERSIONS["macro_daily"]))
    return points
