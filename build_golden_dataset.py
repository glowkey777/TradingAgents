# -*- coding: utf-8 -*-
"""构建 Golden Dataset：锁 6 个日期 daily/15m/option chain + PIT 四时间 + checksum。**immutable**。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from quant_engine.data.config import OPTION_CHAIN_HISTORICAL
from quant_engine.data.loaders.opend_loader import OpenDLoader
from quant_engine.data.validation import validate

try:
    from futu import KLType
except ImportError:
    KLType = None

GOLDEN_DIR = Path(r"F:\Youtube\0413\TradingAgents\golden_dataset")
DATES = ["2013-01-02", "2020-03-16", "2024-01-02",
         "2026-09-23", "2026-09-24", "2026-09-25"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _canonical_json(points) -> bytes:
    return json.dumps([p.model_dump(mode="json") for p in points],
                      sort_keys=True, ensure_ascii=False).encode("utf-8")


def build():
    (GOLDEN_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (GOLDEN_DIR / "canonical").mkdir(parents=True, exist_ok=True)
    (GOLDEN_DIR / "validation").mkdir(parents=True, exist_ok=True)
    (GOLDEN_DIR / "replay").mkdir(parents=True, exist_ok=True)

    loader = OpenDLoader()
    manifest = {
        "dataset_version": "golden_v1",
        "schema_version": "1.0",
        "immutable": True,
        "generated_at": datetime.now().isoformat(),
        "price_basis": "unadjusted",
        "adjustment": "NONE",
        "timezone": "America/New_York",
        "source": "opend",
        "option_chain": dict(OPTION_CHAIN_HISTORICAL),
        "samples": [],
    }

    for d in DATES:
        sample = {"date": d, "daily": None, "intraday_15m": None,
                  "validation": None, "replay": None}

        # ---- daily ----
        daily = loader.fetch_daily("US.SPY", d, d)
        if daily:
            raw_df = loader._q.request_history_kline(
                "US.SPY", start=d, end=d, ktype=KLType.K_DAY)[1]
            raw_df.to_csv(GOLDEN_DIR / "raw" / f"{d}_daily.csv", index=False)
            cj = _canonical_json(daily)
            (GOLDEN_DIR / "canonical" / f"{d}_daily.json").write_bytes(cj)
            rep = validate(daily)
            (GOLDEN_DIR / "validation" / f"{d}_daily.json").write_text(
                json.dumps({"total": rep.total, "duplicates": rep.duplicates,
                            "ohlc_violations": rep.ohlc_violations,
                            "future_data": rep.future_data, "null": rep.null_values},
                           indent=2), encoding="utf-8")
            as_of_close = datetime.fromisoformat(d + " 23:59:59")
            as_of_pre = datetime.fromisoformat(d + " 09:00:00")
            replay = {
                "rows": len(daily),
                "visible_close": sum(1 for p in daily if p.visible_at(as_of_close)),
                "visible_pre": sum(1 for p in daily if p.visible_at(as_of_pre)),
                "pit_ok": sum(1 for p in daily if p.visible_at(as_of_close)) == len(daily)
                and sum(1 for p in daily if p.visible_at(as_of_pre)) == 0,
            }
            (GOLDEN_DIR / "replay" / f"{d}_daily.json").write_text(
                json.dumps(replay, indent=2), encoding="utf-8")
            sample["daily"] = {"rows": len(daily), "status": "OK",
                               "checksum": sha256_bytes(cj),
                               "replay": replay, "validation": {
                                   "duplicates": rep.duplicates, "future_data": rep.future_data,
                                   "null": rep.null_values, "ohlc_violations": rep.ohlc_violations}}
        else:
            sample["daily"] = {"rows": 0, "status": "UNAVAILABLE"}

        # ---- 15m ----
        intr = loader.fetch_intraday("US.SPY", d, d, "15m")
        if intr:
            raw_df = loader._q.request_history_kline(
                "US.SPY", start=d, end=d, ktype=KLType.K_15M)[1]
            raw_df.to_csv(GOLDEN_DIR / "raw" / f"{d}_15m.csv", index=False)
            cj = _canonical_json(intr)
            (GOLDEN_DIR / "canonical" / f"{d}_15m.json").write_bytes(cj)
            rep = validate(intr)
            # 跨 session bar 检查：09:30-16:00
            cross = [p.timestamp for p in intr if p.field == "close"
                     and not ("09:30" <= p.timestamp.strftime("%H:%M") <= "16:00")]
            sample["intraday_15m"] = {"rows": len(intr), "status": "OK",
                                      "checksum": sha256_bytes(cj),
                                      "cross_session_bars": len(cross),
                                      "ohlc_violations": rep.ohlc_violations}
        else:
            sample["intraday_15m"] = {"rows": 0, "status": "UNAVAILABLE"}

        manifest["samples"].append(sample)

    # ---- option chain（当前链，schema 参考；历史链 P8 才验）----
    ret, chain = loader._q.get_option_chain("US.SPY", start="2026-09-25", end="2026-09-25")
    opt = {"rows": len(chain) if chain is not None else 0,
           "columns": list(chain.columns) if chain is not None else [],
           "realtime_recent": OPTION_CHAIN_HISTORICAL["realtime_recent"],
           "historical_pit_reconstruct": OPTION_CHAIN_HISTORICAL["historical_pit_reconstruct"]}
    if chain is not None and not chain.empty:
        (GOLDEN_DIR / "raw" / "option_chain_sample.csv").write_bytes(
            chain.head(20).to_csv(index=False).encode("utf-8"))
        opt["checksum"] = sha256_bytes(chain.head(20).to_csv(index=False).encode("utf-8"))
    manifest["option_chain_sample"] = opt

    manifest_path = GOLDEN_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    loader.close()
    print("Golden Dataset 已生成:", GOLDEN_DIR)
    for s in manifest["samples"]:
        print(f"  {s['date']}: daily={s['daily']['status']}({s['daily']['rows']}) "
              f"15m={s['intraday_15m']['status']}({s['intraday_15m']['rows']})")
    print(f"  option_chain: {opt['rows']} 行, realtime={opt['realtime_recent']}, "
          f"historical={opt['historical_pit_reconstruct']}")


if __name__ == "__main__":
    build()
