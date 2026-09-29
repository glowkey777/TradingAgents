# -*- coding: utf-8 -*-
"""raw 宽表 CSV → PIT 长表（四时间字段）。

日线数据约定：available_at = 该交易日 23:59:59 UTC（收盘后可用）。
即「判断 2024-06-01 状态」能看到 2024-06-01 收盘，看不到 2024-06-02。
"""
from __future__ import annotations

import pandas as pd

RAW = r"F:\Youtube\stock\spy_macro_2013_2026.csv"

# field -> symbol
FIELDS = {
    "spy_close": "SPY",
    "vix": "VIX",
    "us5y": "US5Y",
    "us10y": "US10Y",
    "dxy": "DXY",
    "wti": "WTI",
}


def load_pit(path: str = RAW) -> pd.DataFrame:
    """读 raw 宽表，展开成 PIT 长表。

    返回列：trade_date, symbol, field, value,
            observation_time, published_at, available_at, revision_time, pit_quality
    """
    df = pd.read_csv(path, index_col="date", parse_dates=["date"]).sort_index()
    records = []
    for field, symbol in FIELDS.items():
        for ts, value in df[field].items():
            if pd.isna(value):
                continue
            # 收盘后可用：当日 23:59:59 UTC
            avail = ts.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
            records.append({
                "trade_date": ts.normalize(),
                "symbol": symbol,
                "field": field,
                "value": float(value),
                "observation_time": avail,
                "published_at": avail,
                "available_at": avail,
                "revision_time": pd.NaT,
                "pit_quality": "ok",
            })
    return pd.DataFrame(records)


if __name__ == "__main__":
    pit = load_pit()
    print("PIT 长表行数:", len(pit))
    print("字段数:", pit["field"].nunique(), "| 覆盖交易日:", pit["trade_date"].nunique())
    print("时间范围:", pit["available_at"].min(), "~", pit["available_at"].max())
    print(pit.head(3).to_string())
