# -*- coding: utf-8 -*-
"""P1 CLI：python -m quant_engine.data <query|summary|validate|ingest>。"""
from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from quant_engine.features.base import INGEST, MACRO_CSV
from .macro_metadata import MACRO_SOURCES, MACRO_SYMBOLS, SYMBOL_ALIASES


def parse_as_of(s: str | None) -> datetime | None:
    if not s:
        return None
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone(ZoneInfo("America/New_York")).replace(tzinfo=None)
    return dt


def _daily_long() -> pd.DataFrame:
    frames = [pd.read_parquet(f) for f in sorted((INGEST / "daily").glob("*.parquet"))]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def cmd_query(args) -> None:
    as_of = parse_as_of(args.as_of)
    date = pd.Timestamp(args.date)
    print(f"查询: symbol={args.symbol} field={args.field} "
          f"observation_date={date.date()} as_of={as_of or '∞(无限制)'}")

    if args.symbol in MACRO_SYMBOLS:
        meta = MACRO_SOURCES[args.symbol]
        df = pd.read_csv(MACRO_CSV, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        if meta.field not in df.columns:
            print(f"  ❌ 无字段 {meta.field}（可用: {list(df.columns)}）")
            return
        if date not in df.index:
            print(f"  ❌ {date.date()} 无数据（{meta.symbol} 非交易日或无记录）")
            return
        val = df.loc[date, meta.field]
        if pd.isna(val):
            print(f"  ❌ {date.date()} 值缺失（{meta.symbol} 未 forward-fill）")
            return
        # macro 收盘后可用（当日 23:59:59）；as_of 盘中则不可见
        avail = date.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
        visible = as_of is None or avail <= as_of
        print(f"  value={val:.6f}  unit={meta.unit}  ({meta.description})")
        print(f"  source={meta.source}  ticker={meta.yahoo_ticker}")
        print(f"  available_at={avail}  as_of={as_of or '∞'}")
        print(f"  → {'✅ 可见' if visible else '❌ 不可见（as_of 早于 available_at，PIT 拦截）'}")
        return

    sym = SYMBOL_ALIASES.get(args.symbol, args.symbol)
    df = _daily_long()
    sub = df[(df["symbol"] == sym) & (df["field"] == args.field)].copy()
    sub = sub[pd.to_datetime(sub["observation_time"]).dt.date == date.date()]
    if sub.empty:
        print(f"  ❌ 无数据（symbol={sym} field={args.field} date={date.date()}）")
        return
    sub = sub.sort_values("available_at")
    for _, r in sub.iterrows():
        visible = as_of is None or pd.Timestamp(r["available_at"]) <= as_of
        print(f"  value={r['value']:.6f}  observation_time={r['observation_time']}")
        print(f"  available_at={r['available_at']}  as_of={as_of or '∞'}")
        print(f"  source={r['source']}  dataset_version={r['dataset_version']} "
              f"price_basis={r['price_basis']} adjustment={r['adjustment']}")
        print(f"  → {'✅ 可见' if visible else '❌ 不可见（as_of 早于 available_at，PIT 拦截）'}")


def cmd_summary(args) -> None:
    for freq in ("daily", "15m"):
        frames = [pd.read_parquet(f) for f in sorted((INGEST / freq).glob("*.parquet"))]
        if not frames:
            print(f"{freq}: 无数据")
            continue
        df = pd.concat(frames, ignore_index=True)
        ts = pd.to_datetime(df["timestamp"])
        print(f"{freq}: {len(df)} 行 | {ts.min().date()} ~ {ts.max().date()} "
              f"| symbol={sorted(df['symbol'].unique())} "
              f"| field={sorted(df['field'].unique())} "
              f"| dataset={sorted(df['dataset_version'].unique())}")
    mdf = pd.read_csv(MACRO_CSV, index_col=0, parse_dates=True)
    print(f"macro: {len(mdf)} 行 | {mdf.index.min().date()} ~ {mdf.index.max().date()} "
          f"| 字段={list(mdf.columns)}")


def cmd_validate(args) -> None:
    df = _daily_long()
    if df.empty:
        print("无数据")
        return
    ts = pd.to_datetime(df["timestamp"])
    dup = int(df.duplicated(subset=["timestamp", "field"]).sum())
    future = int((pd.to_datetime(df["available_at"]) < ts).sum())
    print(f"daily 行数={len(df)} 重复 timestamp={dup} available_at<observation={future}")
    # OHLC 违例
    piv = df.pivot_table(index="timestamp", columns="field", values="value")
    if {"high", "low", "open", "close"} <= set(piv.columns):
        hi = piv["high"] >= piv[["open", "close", "low"]].max(axis=1)
        lo = piv["low"] <= piv[["open", "close", "high"]].min(axis=1)
        print(f"OHLC 违例: high违例={int((~hi).sum())} low违例={int((~lo).sum())}")
    if "volume" in piv.columns:
        print(f"volume<0: {int((piv['volume'] < 0).sum())}")
    print("✅ validate 完成")


def cmd_ingest(args) -> None:
    print(f"数据已在 data/ingested/ 入库（SPY daily/15m + macro CSV）。")
    print("重新入库：python ingest_p15.py（15m 全量，含断点续传）")


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m quant_engine.data")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="PIT 查询")
    q.add_argument("--symbol", required=True)
    q.add_argument("--field", default="close")
    q.add_argument("--date", required=True)
    q.add_argument("--as-of", default=None, help="ISO 格式，如 2024-06-03T12:00:00-04:00")
    q.set_defaults(fn=cmd_query)

    s = sub.add_parser("summary", help="数据摘要")
    s.set_defaults(fn=cmd_summary)

    v = sub.add_parser("validate", help="数据质量检查")
    v.set_defaults(fn=cmd_validate)

    i = sub.add_parser("ingest", help="入库说明")
    i.set_defaults(fn=cmd_ingest)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
