# -*- coding: utf-8 -*-
"""数据质量校验：schema / OHLC / 重复 / 未来数据 / 缺失。flag + report，不无脑删除。"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .models import MarketDataPoint

OHLC_TOL = 1e-6  # 复权/浮点误差容差


@dataclass
class ValidationReport:
    total: int = 0
    duplicates: int = 0
    ohlc_violations: int = 0
    future_data: int = 0
    null_values: int = 0
    anomalies: list[str] = field(default_factory=list)

    def failure(self) -> bool:
        """Failure Gate：出现任何硬错误即 FAIL。"""
        return self.duplicates > 0 or self.future_data > 0 or self.null_values > 0

    def render(self) -> str:
        return (f"total={self.total} duplicates={self.duplicates} "
                f"ohlc_violations={self.ohlc_violations} future_data={self.future_data} "
                f"null={self.null_values} anomalies={len(self.anomalies)}")


def validate(points: list[MarketDataPoint]) -> ValidationReport:
    rep = ValidationReport(total=len(points))

    # 1. null 值
    rep.null_values = sum(1 for p in points if pd.isna(p.value))

    # 2. 未来数据：available_at < observation_time 不合理
    for p in points:
        if p.available_at < p.observation_time:
            rep.future_data += 1
            rep.anomalies.append(f"future_data: {p.symbol}.{p.field}@{p.timestamp}")

    # 3. 重复：(symbol, field, observation_time) 唯一
    seen = {}
    for p in points:
        key = (p.symbol, p.field, p.observation_time)
        if key in seen:
            rep.duplicates += 1
        seen[key] = p

    # 4. OHLC 校验（按 timestamp 分组，容差内）
    ohlc = {}
    for p in points:
        if p.field in ("open", "high", "low", "close"):
            ohlc.setdefault((p.symbol, p.timestamp), {})[p.field] = p.value
    for (sym, ts), bar in ohlc.items():
        if all(k in bar for k in ("open", "high", "low", "close")):
            if bar["high"] < max(bar["open"], bar["close"]) - OHLC_TOL:
                rep.ohlc_violations += 1
                rep.anomalies.append(f"ohlc_high: {sym}@{ts}")
            if bar["low"] > min(bar["open"], bar["close"]) + OHLC_TOL:
                rep.ohlc_violations += 1
                rep.anomalies.append(f"ohlc_low: {sym}@{ts}")
            if bar["high"] < bar["low"]:
                rep.ohlc_violations += 1
                rep.anomalies.append(f"ohlc_invert: {sym}@{ts}")

    return rep
