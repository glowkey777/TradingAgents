# -*- coding: utf-8 -*-
"""交易日历。第一版从 canonical 数据提取真实交易日集合，不引入 holidays 依赖、不硬编码假期。

避免 date - timedelta(days=1) 假交易日。周末/美国假期/跨年由真实数据集合覆盖。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd


class TradingCalendar:
    def __init__(self, sessions: set[date]):
        self._sessions = set(sessions)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, date_col: str = "trade_date") -> "TradingCalendar":
        dates = pd.to_datetime(df[date_col]).dt.date
        return cls(set(dates))

    @classmethod
    def from_csv(cls, path: str, date_col: str = "Date") -> "TradingCalendar":
        df = pd.read_csv(path)
        return cls.from_dataframe(df, date_col)

    def is_session(self, d: date) -> bool:
        return d in self._sessions

    def previous_session(self, d: date) -> date:
        cursor = d - timedelta(days=1)
        while cursor not in self._sessions:
            cursor -= timedelta(days=1)
            if cursor < date(1990, 1, 1):
                raise ValueError("no session found before 1990")
        return cursor

    def next_session(self, d: date) -> date:
        cursor = d + timedelta(days=1)
        while cursor not in self._sessions:
            cursor += timedelta(days=1)
            if cursor > date(2100, 1, 1):
                raise ValueError("no session found after 2100")
        return cursor

    def sessions_between(self, start: date, end: date) -> list[date]:
        return sorted(d for d in self._sessions if start <= d <= end)


# 默认日历：从 SPY 日线 CSV（未复权 canonical 的交易日集合）构建
_DEFAULT_CALENDAR = TradingCalendar.from_csv(r"F:\Youtube\stock\spy_daily_2013_2026.csv", date_col="Date")


def get_default_calendar() -> TradingCalendar:
    return _DEFAULT_CALENDAR
