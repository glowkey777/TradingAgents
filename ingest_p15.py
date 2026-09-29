# -*- coding: utf-8 -*-
"""P1.5 全量入库：daily(2013→今) + 15m(2018-09-21→今)，按年/月 partition。

特性：partition / checkpoint / resume / idempotent / retry-backoff / rate-limit /
duplicate detection / gap detection / checksum / row-count reconciliation / manifest。
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from quant_engine.data.calendar import get_default_calendar
from quant_engine.data.loaders.opend_loader import OpenDLoader
from quant_engine.data.validation import validate

DAILY_START = "2013-01-01"
INTRADAY_START = "2018-09-21"   # 探测边界：15m 首日（2018-09-20 及以前 = SOURCE_UNAVAILABLE）
TODAY = "2026-09-25"            # 最后交易日（以 CSV 为准）
INGEST_DIR = Path(r"F:\Youtube\0413\TradingAgents\data\ingested")
MAX_RETRY = 3
RETRY_BASE = 1.0                # 秒
RATE_LIMIT_DELAY = 0.25         # 秒，每次拉取后
BARS_PER_SESSION = 26           # 15m 标准满 bar（09:30–16:00）


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_json(points) -> bytes:
    return json.dumps([p.model_dump(mode="json") for p in points],
                      sort_keys=True, ensure_ascii=False).encode("utf-8")


def month_partitions(start: date, end: date) -> list[tuple[str, date, date]]:
    out = []
    cur = start.replace(day=1)
    while cur <= end:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        out.append((cur.strftime("%Y-%m"), cur, min(nxt - timedelta(days=1), end)))
        cur = nxt
    return out


class Ingester:
    def __init__(self):
        self.loader = OpenDLoader()
        self.cal = get_default_calendar()
        self.manifest_path = INGEST_DIR / "ingestion_manifest.json"
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {"daily": {}, "15m": {}}

    def _save_manifest(self):
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2, ensure_ascii=False),
                                      encoding="utf-8")

    def _fetch(self, frequency: str, start: str, end: str):
        """拉取 + retry/backoff + rate-limit。"""
        last_exc = None
        for attempt in range(1, MAX_RETRY + 1):
            try:
                if frequency == "daily":
                    pts = self.loader.fetch_daily("US.SPY", start, end)
                else:
                    pts = self.loader.fetch_intraday("US.SPY", start, end, "15m")
                time.sleep(RATE_LIMIT_DELAY)
                return pts, None
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(RETRY_BASE * (2 ** (attempt - 1)))
        time.sleep(RATE_LIMIT_DELAY)
        return [], f"{type(last_exc).__name__}: {last_exc}"

    def _ingest_partition(self, frequency: str, partition: str,
                          start: date, end: date) -> dict:
        """拉一个月 → 校验 → 写 parquet → 返回 manifest 条目。"""
        rec = {"partition": partition, "frequency": frequency,
               "source": "opend", "symbol": "US.SPY",
               "start": str(start), "end": str(end)}
        pts, err = self._fetch(frequency, str(start), str(end))

        # 拉取失败
        if err:
            rec.update(status="NETWORK_ERROR", error=err, retry_count=MAX_RETRY)
            return rec

        # SOURCE_UNAVAILABLE：该月无数据（15m 边界前）
        if not pts:
            rec.update(status="SOURCE_UNAVAILABLE", requested_rows=0,
                       received_rows=0, written_rows=0)
            return rec

        # session 集合（从 close 字段提取，避免 5 字段重复计数）
        sessions = sorted(set(p.timestamp.date() for p in pts if p.field == "close"))
        expected_sessions = [d for d in self.cal.sessions_between(start, end)]
        missing = [d for d in expected_sessions if d not in sessions]

        # validation + 重复检测
        rep = validate(pts)
        n_unique = len(set((p.symbol, p.field, p.observation_time) for p in pts))

        # 写 parquet（幂等：文件已存在且 SUCCESS 则跳过）
        out_dir = INGEST_DIR / frequency
        out_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = out_dir / f"{partition}.parquet"
        df = pd.DataFrame([p.model_dump() for p in pts])
        df.to_parquet(parquet_path, index=False)

        rec.update(
            status="SUCCESS" if not rep.failure() else "VALIDATION_FAILURE",
            requested_rows=len(expected_sessions) * (5 if frequency == "daily" else BARS_PER_SESSION),
            received_rows=len(pts),
            written_rows=len(pts),
            duplicate_rows=len(pts) - n_unique,
            missing_sessions=len(missing),
            sessions_with_data=len(sessions),
            expected_sessions=len(expected_sessions),
            validation_status="PASS" if not rep.failure() else "FAIL",
            ohlc_violations=rep.ohlc_violations,
            future_data=rep.future_data,
            null_values=rep.null_values,
            checksum=sha256_bytes(canonical_json(pts)),
            ingested_at=datetime.now().isoformat(),
            schema_version="1.0",
        )
        return rec

    def run(self, frequency: str, start: str, end: str):
        print(f"\n=== {frequency} ingestion: {start} → {end} ===")
        partitions = month_partitions(date.fromisoformat(start), date.fromisoformat(end))
        print(f"共 {len(partitions)} 个月 partition")
        for partition, ps, pe in partitions:
            existing = self.manifest[frequency].get(partition)
            if existing and existing.get("status") == "SUCCESS":
                print(f"  ⏭ {partition}: 已完成，跳过")
                continue
            rec = self._ingest_partition(frequency, partition, ps, pe)
            self.manifest[frequency][partition] = rec
            self._save_manifest()
            flag = {"SUCCESS": "✅", "SOURCE_UNAVAILABLE": "⬜",
                    "NETWORK_ERROR": "❌", "VALIDATION_FAILURE": "🚫"}.get(rec["status"], "?")
            print(f"  {flag} {partition}: {rec['status']} "
                  f"sessions={rec.get('sessions_with_data','-')}/{rec.get('expected_sessions','-')} "
                  f"rows={rec.get('written_rows','-')} "
                  f"missing={rec.get('missing_sessions','-')}")


def build_coverage(manifest: dict) -> dict:
    """生成 DATA_COVERAGE 表。"""
    coverage = {}
    for freq in ("daily", "15m"):
        parts = manifest[freq]
        ok = {k: v for k, v in parts.items() if v.get("status") == "SUCCESS"}
        if not ok:
            coverage[freq] = {"status": "EMPTY"}
            continue
        keys = sorted(ok)
        sessions = sum(v.get("sessions_with_data", 0) for v in ok.values())
        missing = sum(v.get("missing_sessions", 0) for v in ok.values())
        bars = sum(v.get("written_rows", 0) for v in ok.values())
        if freq == "daily":
            expected_bars = sessions * 5
        else:
            expected_bars = sum(v.get("requested_rows", 0) for v in ok.values())
        coverage[freq] = {
            "available_from": keys[0],
            "available_to": keys[-1],
            "trading_days": sessions,
            "expected_bars": expected_bars,
            "actual_bars": bars,
            "missing_bars": expected_bars - bars,
            "missing_sessions": missing,
            "status": "COMPLETE" if missing == 0 else "PARTIAL",
        }
    return coverage


def main():
    INGEST_DIR.mkdir(parents=True, exist_ok=True)
    ing = Ingester()
    ing.run("daily", DAILY_START, TODAY)
    ing.run("15m", INTRADAY_START, TODAY)
    ing.loader.close()

    coverage = build_coverage(ing.manifest)
    (INGEST_DIR / "data_coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print("DATA_COVERAGE")
    print("=" * 60)
    for freq, c in coverage.items():
        print(f"  {freq}: {c.get('status')} from={c.get('available_from')} "
              f"to={c.get('available_to')} sessions={c.get('trading_days')} "
              f"bars={c.get('actual_bars')}/{c.get('expected_bars')} "
              f"missing_sessions={c.get('missing_sessions')}")


if __name__ == "__main__":
    main()
