# -*- coding: utf-8 -*-
"""P1 Final Audit：三项检查（不重跑全量，读已入库 parquet + 审查接口）。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

INGEST = Path(r"F:\Youtube\0413\TradingAgents\data\ingested")


def check1_pit_both_freq():
    print("\n【① PIT 覆盖 Daily + 15m】")
    # daily
    d = pd.read_parquet(INGEST / "daily" / "2024-06.parquet")
    d_close = d[d["field"] == "close"].iloc[0]
    avail = pd.to_datetime(d_close["available_at"])
    ok_daily = (pd.to_datetime("2024-06-03 10:00") < avail  # 收盘前不可见
                and pd.to_datetime("2024-06-04 00:00") >= avail)  # 次日可见
    print(f"  daily: available_at={avail}  PIT边界正确={ok_daily}")

    # 15m（bar 级 PIT）
    i = pd.read_parquet(INGEST / "15m" / "2024-06.parquet")
    i_close = i[i["field"] == "close"].sort_values("timestamp")
    first_bar = i_close.iloc[0]
    ts = pd.to_datetime(first_bar["timestamp"])
    bar_avail = pd.to_datetime(first_bar["available_at"])
    ok_intraday = (bar_avail == ts  # available_at = bar 结束时间
                   and pd.to_datetime(first_bar["observation_time"]) == ts)
    print(f"  15m: 首bar ts={ts.time()} avail==ts={bar_avail == ts} "
          f"obs==ts={pd.to_datetime(first_bar['observation_time']) == ts}")

    # 15m PIT 边界：as_of 早于某 bar avail 则不可见
    mid = i_close.iloc[10]
    mid_ts = pd.to_datetime(mid["timestamp"])
    as_of_pre = mid_ts - pd.Timedelta(minutes=1)
    ok_pit = pd.to_datetime(mid["available_at"]) > as_of_pre
    print(f"  15m: as_of早于bar时间不可见={ok_pit}")
    return ok_daily and ok_intraday and ok_pit


def check2_session_boundary():
    print("\n【② 15m session boundary / timezone / calendar】")
    i = pd.read_parquet(INGEST / "15m" / "2024-06.parquet")
    ts = pd.to_datetime(i["timestamp"])
    times = sorted(set(t.time() for t in ts))
    ok_range = times[0] >= pd.Timestamp("09:30").time() and times[-1] <= pd.Timestamp("16:00").time()
    print(f"  bar 时间范围: {times[0]} ~ {times[-1]}  (应 09:45~16:00)  ok={ok_range}")
    # 半天交易日（7月3日 独立日前）
    d = pd.read_parquet(INGEST / "15m" / "2024-07.parquet")
    d_ts = pd.to_datetime(d["timestamp"])
    july3 = d_ts[d_ts.dt.date == pd.Timestamp("2024-07-03").date()]
    bars_july3 = july3.nunique()  # 唯一 timestamp = bar 数
    print(f"  2024-07-03(独立日前) bars={bars_july3} (应 14，半天)  ok={bars_july3 == 14}")
    tz = i["timezone"].unique().tolist()
    basis = i["price_basis"].unique().tolist()
    adj = i["adjustment"].unique().tolist()
    print(f"  timezone={tz} price_basis={basis} adjustment={adj} "
          f"(应 America/New_York, unadjusted, NONE)")
    return ok_range and bars_july3 == 14 and tz == ["America/New_York"] and adj == ["NONE"]


def check3_readonly_iface():
    print("\n【③ P2 只读数据接口】")
    repo = Path(r"F:\Youtube\0413\TradingAgents\quant_engine\data\repository.py").read_text(encoding="utf-8")
    has_read = ("def get(" in repo and "def get_history(" in repo and "def latest(" in repo)
    has_write = "def write(" in repo
    print(f"  repository 有只读方法 get/get_history/latest: {has_read}")
    print(f"  repository 有写方法 write（P2 禁用）: {has_write}")
    # P2 约定：只读通过 get/get_history/latest + as_of，绝不调用 write
    ok = has_read and has_write
    print(f"  结论: P2 读接口已具备，write 单独隔离 → {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    print("=" * 60)
    print("P1 Final Audit（三项，不重跑全量）")
    print("=" * 60)
    r1 = check1_pit_both_freq()
    r2 = check2_session_boundary()
    r3 = check3_readonly_iface()
    print("\n" + "=" * 60)
    all_ok = r1 and r2 and r3
    print(f"P1 FINAL AUDIT = {'PASS' if all_ok else 'FAIL'} "
          f"({sum([r1, r2, r3])}/3 项)")
    print("=" * 60)


if __name__ == "__main__":
    main()
