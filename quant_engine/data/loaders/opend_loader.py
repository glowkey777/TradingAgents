# -*- coding: utf-8 -*-
"""OpenD Loader：SPY 未复权 canonical 主数据源（日线 + 15m + 期权能力探测）。

futu SDK 10.x：request_history_kline 返回三元组 (ret, data, page_req_key)。
K线 DataFrame 列：code/name/time_key/open/close/high/low/volume/...
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from ..config import DATASET_VERSIONS, AVAILABILITY_POLICY, TIMEZONE
from ..models import MarketDataPoint

try:
    from futu import OpenQuoteContext, KLType, RET_OK
    _HAS_FUTU = True
except ImportError:
    _HAS_FUTU = False

KL_MAP = {"1m": KLType.K_1M, "5m": KLType.K_5M, "15m": KLType.K_15M,
          "30m": KLType.K_30M, "1h": KLType.K_60M, "daily": KLType.K_DAY}

INTERVAL_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "daily": 0}


class OpenDLoader:
    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        if not _HAS_FUTU:
            raise ImportError("futu SDK not installed")
        self._q = OpenQuoteContext(host, port)

    def _to_points(self, df: pd.DataFrame, symbol: str, frequency: str) -> list[MarketDataPoint]:
        points = []
        interval = INTERVAL_MIN[frequency]
        for _, row in df.iterrows():
            ts = pd.to_datetime(row["time_key"])
            # available_at = 该K线结束后可用（日线=收盘后，日内=该根结束）
            if frequency == "daily":
                avail = ts.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                obs = ts.normalize() + pd.Timedelta(hours=16)  # 16:00 ET 收盘
            else:
                obs = ts  # time_key 是 bar 结束时间（首根09:45=09:30-09:45，末根16:00=15:45-16:00）
                avail = ts
            base = dict(
                symbol=symbol, source="opend", frequency=frequency,
                timezone=TIMEZONE, price_basis="unadjusted", adjustment="NONE",
                dataset_version=DATASET_VERSIONS.get(
                    "spy_daily" if frequency == "daily" else "spy_intraday"),
            )
            for field in ("open", "high", "low", "close"):
                points.append(MarketDataPoint(
                    timestamp=ts, field=field, value=float(row[field]),
                    observation_time=obs, available_at=avail, **base))
            points.append(MarketDataPoint(
                timestamp=ts, field="volume", value=float(row["volume"]),
                observation_time=obs, available_at=avail, **base))
        return points

    def fetch_daily(self, symbol: str, start: str, end: str) -> list[MarketDataPoint]:
        ret, df, _ = self._q.request_history_kline(symbol, start=start, end=end,
                                                   ktype=KLType.K_DAY, max_count=1000)
        if ret != RET_OK or df is None or df.empty:
            return []
        return self._to_points(df, symbol, "daily")

    def fetch_intraday(self, symbol: str, start: str, end: str, frequency: str = "15m") -> list[MarketDataPoint]:
        ret, df, _ = self._q.request_history_kline(symbol, start=start, end=end,
                                                   ktype=KL_MAP[frequency], max_count=1000)
        if ret != RET_OK or df is None or df.empty:
            return []
        return self._to_points(df, symbol, frequency)

    def probe_option_chain(self, symbol: str, d: str) -> dict:
        """能力探测：期权链能否拉、有多少行、含哪些字段。返回能力报告 dict。"""
        ret, df = self._q.get_option_chain(symbol, start=d, end=d)
        return {
            "available": ret == RET_OK and df is not None and not df.empty,
            "rows": len(df) if df is not None else 0,
            "columns": list(df.columns) if df is not None else [],
            "historical_chain_supported": None,  # 待后续探测（get_option_chain 只给当前）
        }

    def close(self):
        self._q.close()
