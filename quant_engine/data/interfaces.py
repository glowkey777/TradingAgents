# -*- coding: utf-8 -*-
"""P1 接口契约（Protocol）。数据源 / 仓储 / 日历 / PIT 读取 的统一接口。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, Sequence

from .models import MarketDataPoint


class TradingCalendar(Protocol):
    """交易日历抽象（禁 timedelta 假交易日）。"""
    def is_session(self, d: date) -> bool: ...
    def previous_session(self, d: date) -> date: ...
    def next_session(self, d: date) -> date: ...
    def sessions_between(self, start: date, end: date) -> list[date]: ...


class PITDataReader(Protocol):
    """按 as_of 读取，严格执行 available_at <= as_of。"""
    def get(self, symbol: str, field: str,
            observation_date: date, as_of: datetime) -> MarketDataPoint | None: ...
    def get_history(self, symbol: str, field: str,
                    start: date, end: date, as_of: datetime) -> list[MarketDataPoint]: ...


class MarketDataRepository(Protocol):
    """Canonical 仓储（Parquet）。"""
    def write(self, rows: Sequence[MarketDataPoint]) -> None: ...
    def get(self, symbol: str, field: str,
            start: date, end: date, as_of: datetime | None = None) -> list[MarketDataPoint]: ...
    def latest(self, symbol: str, field: str,
               as_of: datetime | None = None) -> MarketDataPoint | None: ...
