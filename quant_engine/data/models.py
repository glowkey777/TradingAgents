# -*- coding: utf-8 -*-
"""Quant Data 强类型模型（P1 Data Contract 落地）。

Canonical price = 未复权价（用户拍板）。adjustment 必须显式记录，禁止数据层偷偷复权。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Frequency = Literal["daily", "1m", "5m", "15m", "30m", "1h"]
PriceBasis = Literal["unadjusted", "adjusted"]


class MarketDataPoint(BaseModel):
    """统一的市场数据点（OHLCV / 宏观 / 指数）。"""
    timestamp: datetime                      # 观测时点（K线所在交易时段）
    symbol: str
    field: str                               # open/high/low/close/volume/vix/us5y/...
    value: float
    source: str                              # "opend" | "yfinance" | "csv"

    observation_time: datetime               # 数据描述的时点
    available_at: datetime                   # 市场参与者最早可用时点（PIT 核心）
    revision_time: datetime | None = None
    ingested_at: datetime | None = None      # 数据摄入本系统的时间（audit/reproducibility）

    frequency: Frequency
    timezone: str = "America/New_York"
    unit: str | None = None                  # "percent" | "usd" | "index" | None

    price_basis: PriceBasis = "unadjusted"   # 关键：canonical=unadjusted
    adjustment: str = "NONE"                 # 显式记录复权（NONE/SPLIT/DIVIDEND/...）

    dataset_version: str = ""
    is_revised: bool = False
    is_estimated: bool = False

    def visible_at(self, as_of: datetime) -> bool:
        """PIT 铁律：as_of 时点该数据是否可见。"""
        if self.available_at > as_of:
            return False
        if self.revision_time is not None and self.revision_time <= as_of:
            return False
        return True


class OptionDataPoint(BaseModel):
    """期权数据点（P1 定义 schema，P8 才实现历史回测）。"""
    timestamp: datetime
    underlying: str
    expiration: date
    strike: float
    option_type: Literal["call", "put"]

    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: int | None = None
    open_interest: int | None = None

    iv: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None

    available_at: datetime
    source: str
    dataset_version: str

    def visible_at(self, as_of: datetime) -> bool:
        """期权链同样满足 PIT：as_of 早于 available_at 则不可见。"""
        return self.available_at <= as_of


class DataSourceMetadata(BaseModel):
    """数据源元数据（Benchmark / 版本追踪）。"""
    source: str
    symbol: str
    field: str
    frequency: str
    timezone: str = "America/New_York"
    unit: str | None = None
    availability_policy: str               # session_close_plus_buffer / vendor_timestamp / ...
    revision_policy: str
    price_basis: PriceBasis = "unadjusted"
    adjustment: str = "NONE"
    first_observation: datetime | None = None
    last_observation: datetime | None = None
    ingested_at: datetime | None = None
    dataset_version: str = ""
