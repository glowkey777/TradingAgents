# -*- coding: utf-8 -*-
"""Golden Dataset Regression：重跑当前 pipeline，对比 checksum / 行数 / PIT / schema 不变式。
只读 Golden Dataset，绝不修改。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from quant_engine.data.config import OPTION_CHAIN_HISTORICAL
from quant_engine.data.loaders.opend_loader import OpenDLoader

GOLDEN_DIR = Path(r"F:\Youtube\0413\TradingAgents\golden_dataset")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canonical_json(points) -> bytes:
    return json.dumps([p.model_dump(mode="json") for p in points],
                      sort_keys=True, ensure_ascii=False).encode("utf-8")


def _schema_invariants(points) -> list[str]:
    """返回违反的不变式列表（空 = 全过）。"""
    viol = []
    for p in points:
        if p.price_basis != "unadjusted":
            viol.append(f"price_basis={p.price_basis}")
        if p.adjustment != "NONE":
            viol.append(f"adjustment={p.adjustment}")
        if p.available_at < p.observation_time:
            viol.append(f"future: {p.field}")
    # 15m bar end-time：observation_time 必须 == timestamp（16:00 = 15:45-16:00）
    for p in points:
        if p.frequency != "daily" and p.observation_time != p.timestamp:
            viol.append(f"bar_end_time_mismatch: {p.field}@{p.timestamp}")
            break
    return viol


def regression():
    manifest = json.loads((GOLDEN_DIR / "manifest.json").read_text(encoding="utf-8"))
    loader = OpenDLoader()
    results = []

    for sample in manifest["samples"]:
        d = sample["date"]

        # daily
        if sample["daily"]["status"] == "OK":
            daily = loader.fetch_daily("US.SPY", d, d)
            cj = _canonical_json(daily)
            checksum = sha256_bytes(cj)
            as_of_close = datetime.fromisoformat(d + " 23:59:59")
            as_of_pre = datetime.fromisoformat(d + " 09:00:00")
            pit_ok = (sum(1 for p in daily if p.visible_at(as_of_close)) == len(daily)
                      and sum(1 for p in daily if p.visible_at(as_of_pre)) == 0)
            viol = _schema_invariants(daily)
            ok = (checksum == sample["daily"]["checksum"]
                  and len(daily) == sample["daily"]["rows"]
                  and pit_ok and not viol)
            results.append((f"{d} daily", ok,
                            f"rows={len(daily)} checksum={'OK' if checksum == sample['daily']['checksum'] else 'MISMATCH'} "
                            f"pit={pit_ok} invariants={viol or 'OK'}"))
        elif sample["daily"]["status"] == "UNAVAILABLE":
            results.append((f"{d} daily", True, "UNAVAILABLE (基线即无)"))

        # 15m
        if sample["intraday_15m"]["status"] == "OK":
            intr = loader.fetch_intraday("US.SPY", d, d, "15m")
            cj = _canonical_json(intr)
            checksum = sha256_bytes(cj)
            viol = _schema_invariants(intr)
            cross = [p for p in intr if p.field == "close"
                     and not ("09:30" <= p.timestamp.strftime("%H:%M") <= "16:00")]
            ok = (checksum == sample["intraday_15m"]["checksum"]
                  and len(intr) == sample["intraday_15m"]["rows"]
                  and len(cross) == sample["intraday_15m"]["cross_session_bars"]
                  and not viol)
            results.append((f"{d} 15m", ok,
                            f"rows={len(intr)} checksum={'OK' if checksum == sample['intraday_15m']['checksum'] else 'MISMATCH'} "
                            f"cross_session={len(cross)} invariants={viol or 'OK'}"))
        elif sample["intraday_15m"]["status"] == "UNAVAILABLE":
            results.append((f"{d} 15m", True, "UNAVAILABLE (基线即无)"))

    # option chain 不变式
    opt = manifest["option_chain_sample"]
    opt_ok = (opt["realtime_recent"] == "VERIFIED"
              and opt["historical_pit_reconstruct"] == "UNVERIFIED"
              and OPTION_CHAIN_HISTORICAL["historical_pit_reconstruct"] == "UNVERIFIED")
    results.append(("option_chain 状态", opt_ok,
                    f"realtime={opt['realtime_recent']} historical={opt['historical_pit_reconstruct']}"))

    loader.close()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("=" * 62)
    print("Golden Dataset Regression")
    print("=" * 62)
    for name, ok, detail in results:
        print(f"  {'✅' if ok else '❌'} {name}: {detail}")
    print("=" * 62)
    print(f"GOLDEN_DATASET = {'PASS' if passed == total else 'FAIL'} ({passed}/{total})")
    return passed == total


if __name__ == "__main__":
    raise SystemExit(0 if regression() else 1)
