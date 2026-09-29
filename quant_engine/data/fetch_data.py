# -*- coding: utf-8 -*-
"""P1 数据层：拉取 SPY + 宏观数据（VIX/5Y/10Y/DXY/WTI），统一长表 schema。

Schema（ChatGPT 方案 point-in-time 约定）：
  每条日线观测的 available_at = 该交易日收盘时刻（16:00 ET）。
  即「2024-06-01 的状态判断」只允许用 <= 2024-06-01 收盘的数据，
  2024-06-02 及之后的数据在那一刻不可见。宽表 + 收盘可用的约定，
  等价于为每列记录 available_at = 收盘时间。
"""
import sys
import yfinance as yf
import pandas as pd

OUT = r"F:\Youtube\stock\spy_macro_2013_2026.csv"
START = "2013-01-01"

# 每个字段 -> (主 ticker, 备用 ticker)
TICKERS = {
    "spy_close": ("SPY", None),
    "vix":       ("^VIX", None),
    "us5y":      ("^FVX", None),        # 5 年期国债收益率
    "us10y":     ("^TNX", None),        # 10 年期国债收益率
    "dxy":       ("DX-Y.NYB", "DX=F"),  # 美元指数
    "wti":       ("CL=F", None),        # WTI 原油期货
}


def fetch_one(ticker: str):
    df = yf.download(ticker, start=START, auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise ValueError("empty")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close


def main():
    data = {}
    for name, (tk, alt) in TICKERS.items():
        series = None
        for candidate in (tk, alt):
            if candidate is None:
                continue
            try:
                series = fetch_one(candidate)
                break
            except Exception as exc:
                print(f"  {name} <- {candidate} 失败: {exc}", file=sys.stderr)
        if series is None:
            print(f"[跳过] {name}: 所有 ticker 都拉不到", file=sys.stderr)
            continue
        data[name] = series.rename(name)
        print(f"[OK] {name:10s} ({tk}): {len(series)} 行  "
              f"{series.index[0].date()} ~ {series.index[-1].date()}")

    df = pd.DataFrame(data).sort_index()
    df.index.name = "date"
    before = len(df)
    df = df.dropna()
    print(f"\n合并对齐后: {len(df)} 行 (dropna 前 {before} 行)")
    print(f"列: {list(df.columns)}")
    print(f"范围: {df.index[0].date()} ~ {df.index[-1].date()}")
    df.to_csv(OUT)
    print(f"已保存: {OUT}")


if __name__ == "__main__":
    main()
