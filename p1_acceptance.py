# -*- coding: utf-8 -*-
"""P1 验收：6 项基线 + 小规模全链路回放。**不全量入库**。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from quant_engine.data.calendar import get_default_calendar
from quant_engine.data.config import REPOSITORY_DIR
from quant_engine.data.loaders.opend_loader import OpenDLoader
from quant_engine.data.loaders.local_csv import load_spy_daily_csv
from quant_engine.data.models import MarketDataPoint, OptionDataPoint
from quant_engine.data.repository import ParquetRepository
from quant_engine.data.validation import validate

REPLAY_DATES = ["2013-01-02", "2020-03-16", "2024-01-02",
                "2026-09-23", "2026-09-24", "2026-09-25"]
RESULTS = []


def mark(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}  {detail}")


def check1_pit_fields():
    print("\n【项1】PIT 四时间字段")
    fields = set(MarketDataPoint.model_fields)
    need = {"timestamp", "observation_time", "available_at", "ingested_at", "revision_time"}
    mark("字段齐全(含 ingested_at)", need <= fields,
         f"有={sorted(f for f in need if f in fields)}")
    mark("as_of 是查询参数(非字段)", "as_of" not in fields,
         "as_of 通过 visible_at(as_of)/get(..., as_of) 传入")


def check2_visible_at():
    print("\n【项2】visible_at(as_of) 严格禁止未来数据")
    base = dict(symbol="SPY", field="close", value=100.0, source="opend",
                timestamp=datetime(2026, 9, 25), observation_time=datetime(2026, 9, 25, 16),
                available_at=datetime(2026, 9, 25, 23, 59, 59),
                frequency="daily", timezone="America/New_York", price_basis="unadjusted")
    p = MarketDataPoint(**base)
    ok1 = not p.visible_at(datetime(2026, 9, 25, 10, 0))       # 收盘前不可见
    ok2 = p.visible_at(datetime(2026, 9, 25, 23, 59, 59))      # available_at 时点可见
    ok3 = not p.visible_at(datetime(2026, 9, 24, 23, 59, 59))  # 前一天不可见
    mark("收盘前(as_of=10:00)不可见", ok1, "")
    mark("available_at 时点可见", ok2, "")
    mark("前一日不可见", ok3, "")


def check3_session_consistency(loader):
    print("\n【项3】OpenD 日线 vs 15m 时间戳/session 一致")
    daily = loader.fetch_daily("US.SPY", "2026-09-25", "2026-09-25")
    intr = loader.fetch_intraday("US.SPY", "2026-09-25", "2026-09-25", "15m")
    if not daily or not intr:
        mark("拉取日线+15m", False, f"daily={len(daily)} intraday={len(intr)}")
        return
    d_close = [p.value for p in daily if p.field == "close"][0]
    i_close = [p.value for p in intr if p.field == "close"][-1]   # 最后一根 15m
    times = sorted(set(p.timestamp.time() for p in intr))
    mark("15m 全部落在 09:30-16:00", times[0] >= pd.Timestamp("09:30").time()
         and times[-1] <= pd.Timestamp("16:00").time(), f"首根={times[0]} 末根={times[-1]}")
    mark("日线 close ≈ 15m 末根 close", abs(d_close - i_close) < 0.05,
         f"日线={d_close:.2f} 15m末={i_close:.2f}")
    d_obs = [p.observation_time for p in daily if p.field == "close"][0]
    i_obs = max(p.observation_time for p in intr)
    mark("session 结束(16:00)一致", d_obs == i_obs, f"日线obs={d_obs} 15m末obs={i_obs}")


def check4_date_gaps():
    print("\n【项4】2013→今天日期断层（用 CSV 3454 交易日）")
    csv_pts = load_spy_daily_csv()
    dates = sorted(set(p.timestamp.date() for p in csv_pts if p.field == "close"))
    gaps = []
    for a, b in zip(dates, dates[1:]):
        d = (b - a).days
        if d > 4:  # 周末+长假 > 4 天才可疑
            gaps.append((a, b, d))
    mark("交易日总数", len(dates) == 3454, f"{len(dates)} 天")
    mark("无断层(间隔>4天)", len(gaps) == 0,
         f"{len(gaps)} 处: {gaps[:5]}")


def check5_intraday_anomalies(loader):
    print("\n【项5】15m 异常 bar / 重复 bar / 跨 session bar")
    intr = loader.fetch_intraday("US.SPY", "2026-09-23", "2026-09-25", "15m")
    if not intr:
        mark("拉取 15m", False, "空")
        return
    ts = [p.timestamp for p in intr if p.field == "close"]
    dup = len(ts) - len(set(ts))
    rep = validate(intr)
    cross = [t for t in ts if not (pd.Timestamp("09:30").time() <= t.time() <= pd.Timestamp("16:00").time())]
    mark("拉取 15m", True, f"{len(intr)} 条 (3 天)")
    mark("无重复 bar", dup == 0, f"重复={dup}")
    mark("无跨 session bar", len(cross) == 0, f"跨session={len(cross)}")
    mark("OHLC 无违例", rep.ohlc_violations == 0, f"viol={rep.ohlc_violations}")


def check6_option_pit():
    print("\n【项6】期权链 as_of 满足 PIT")
    opt = OptionDataPoint(timestamp=datetime(2026, 9, 25, 15, 30),
                          underlying="SPY", expiration=date(2026, 9, 30), strike=760.0,
                          option_type="call", available_at=datetime(2026, 9, 25, 15, 30),
                          source="opend", dataset_version="opend_options_v1")
    ok1 = opt.visible_at(datetime(2026, 9, 25, 15, 30))
    ok2 = not opt.visible_at(datetime(2026, 9, 25, 15, 0))
    mark("available_at 时点可见", ok1, "")
    mark("as_of 早于 available_at 不可见", ok2, "")


def replay(loader, repo):
    print("\n【② 小规模全链路回放】写=读=as_of 可见")
    for d in REPLAY_DATES:
        pts = loader.fetch_daily("US.SPY", d, d)
        rep = validate(pts)
        if not pts:
            mark(f"{d}", False, "OpenD 无数据")
            continue
        repo.write(f"replay_{d}", pts)
        loaded = repo.load(f"replay_{d}")
        as_of_close = datetime.fromisoformat(d + " 23:59:59")
        as_of_pre = datetime.fromisoformat(d + " 09:00:00")
        n_visible_close = sum(1 for p in loaded if p.visible_at(as_of_close))
        n_visible_pre = sum(1 for p in loaded if p.visible_at(as_of_pre))
        write_eq_read = len(pts) == len(loaded)
        gate_ok = not rep.failure()
        pit_ok = n_visible_close == len(loaded) and n_visible_pre == 0
        ok = write_eq_read and gate_ok and pit_ok
        mark(f"{d}", ok,
             f"写{len(pts)}=读{len(loaded)} gate={'PASS' if gate_ok else 'FAIL'} "
             f"收盘后可见{n_visible_close}/盘中可见{n_visible_pre}")


def main():
    print("=" * 62)
    print("P1 验收（6 项基线 + 小规模回放）")
    print("=" * 62)
    loader = OpenDLoader()
    repo = ParquetRepository(REPOSITORY_DIR)
    check1_pit_fields()
    check2_visible_at()
    check3_session_consistency(loader)
    check4_date_gaps()
    check5_intraday_anomalies(loader)
    check6_option_pit()
    replay(loader, repo)
    loader.close()

    print("\n" + "=" * 62)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"验收结果: {passed}/{total} PASS")
    for name, ok, _ in RESULTS:
        if not ok:
            print(f"  ❌ {name}")
    print("=" * 62)


if __name__ == "__main__":
    main()
