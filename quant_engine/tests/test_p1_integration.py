# -*- coding: utf-8 -*-
"""P1 集成测试 + Benchmark（真实数据跑通全链路）。"""
from __future__ import annotations

from datetime import date, datetime

from quant_engine.data.calendar import get_default_calendar
from quant_engine.data.config import REPOSITORY_DIR
from quant_engine.data.loaders.opend_loader import OpenDLoader
from quant_engine.data.loaders.local_csv import load_spy_daily_csv
from quant_engine.data.repository import ParquetRepository
from quant_engine.data.validation import validate


def main():
    print("=" * 60)
    print("P1 数据层集成测试 + Benchmark")
    print("=" * 60)

    # 1. OpenD 拉 SPY 日线（canonical 未复权）
    loader = OpenDLoader()
    pts = loader.fetch_daily("US.SPY", "2026-08-01", "2026-09-25")
    print(f"\n[1] OpenD 日线 → MarketDataPoint: {len(pts)} 条")
    if pts:
        sample = pts[0]
        print(f"    样例: {sample.symbol} {sample.field}={sample.value} "
              f"basis={sample.price_basis} freq={sample.frequency}")

    # 2. Validation（Failure Gate）
    rep = validate(pts)
    print(f"\n[2] Validation: {rep.render()}")
    print(f"    Failure Gate: {'FAIL ❌' if rep.failure() else 'PASS ✅'}")

    # 3. Parquet Repository 写读
    repo = ParquetRepository(REPOSITORY_DIR)
    repo.write("spy_daily_opend_v1", pts)
    loaded = repo.load("spy_daily_opend_v1")
    print(f"\n[3] Parquet Repository 写 {len(pts)} / 读 {len(loaded)}")

    # 4. PIT 读取（未来数据不可见）
    as_of = datetime(2026, 9, 23, 23, 59, 59)
    hist = repo.get_history("US.SPY", "close", date(2026, 9, 18), date(2026, 9, 25),
                            as_of, "spy_daily_opend_v1")
    max_d = max((p.observation_time.date() for p in hist), default=None)
    print(f"\n[4] PIT 读取 as_of=2026-09-23: {len(hist)} 条, 最后可见 {max_d} "
          f"(应 <= 09-23，09-24/25 不可见)")

    # 5. 交易日历（非交易日识别）
    cal = get_default_calendar()
    print(f"\n[5] 日历: 2024-06-01 交易日? {cal.is_session(date(2024, 6, 1))} (应 False，周六)")
    print(f"    2024-05-31 交易日? {cal.is_session(date(2024, 5, 31))} (应 True)")
    print(f"    previous_session(2024-06-03) = {cal.previous_session(date(2024, 6, 3))} (应 05-31)")

    # 6. CSV cross-check（复权价，隔离）
    csv_pts = load_spy_daily_csv()
    print(f"\n[6] CSV cross-check: {len(csv_pts)} 条, basis={csv_pts[0].price_basis} "
          f"(应 adjusted，不复权混用)")

    print("\n" + "=" * 60)
    print("Benchmark 摘要")
    print("=" * 60)
    print(f"OpenD SPY 日线(2026-08~09): {len(pts)} 条")
    print(f"  字段: {sorted(set(p.field for p in pts))}")
    print(f"  日期范围: {min(p.observation_time.date() for p in pts)} ~ "
          f"{max(p.observation_time.date() for p in pts)}")
    print(f"  duplicates={rep.duplicates} null={rep.null_values} "
          f"future={rep.future_data} ohlc_viol={rep.ohlc_violations}")


if __name__ == "__main__":
    main()
