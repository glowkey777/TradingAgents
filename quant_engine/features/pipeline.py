# -*- coding: utf-8 -*-
"""Feature Pipeline：build_features / get_features（PIT-safe，deterministic）。"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from .base import Feature, load_wide, SOURCE_DATA_VERSION
from .models import FeatureDataPoint
from .registry import FeatureRegistry

# 导入 feature 定义模块，触发自动注册
from . import daily as _daily  # noqa: F401
from . import intraday as _intraday  # noqa: F401
from . import macro as _macro  # noqa: F401


def _available_at(ts: pd.Timestamp, frequency: str) -> datetime:
    """feature 的 available_at 继承源数据 PIT。"""
    if frequency == "daily":
        return (ts.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)).to_pydatetime()
    return ts.to_pydatetime()  # 15m/30m/1h：bar 结束时间即可用


def build_features(symbol: str, frequency: str, start: str | None = None,
                   end: str | None = None, as_of: datetime | None = None,
                   feature_names: list[str] | None = None) -> list[FeatureDataPoint]:
    """计算指定频率的所有 feature，输出 FeatureDataPoint 列表（PIT-safe）。"""
    load_freq = "15m" if frequency in ("15m", "30m", "1h", "session") else frequency
    wide = load_wide(load_freq, as_of=as_of)
    if wide.empty:
        return []
    idx = wide.index
    if start is not None:
        idx = idx[idx >= pd.Timestamp(start)]
    if end is not None:
        idx = idx[idx < pd.Timestamp(end) + pd.Timedelta(days=1)]  # end 含当天
    wide = wide.loc[idx]

    names = feature_names or [d.feature_name for d in FeatureRegistry.all()
                              if d.frequency == frequency]
    points: list[FeatureDataPoint] = []
    for name in names:
        inst: Feature = FeatureRegistry.instance(name)
        try:
            series = inst.compute(wide)
        except Exception:
            continue
        for ts, val in series.items():
            if pd.isna(val):
                flag, value = "INSUFFICIENT_HISTORY", None
            else:
                flag, value = "OK", float(val)
            points.append(FeatureDataPoint(
                feature_name=name, symbol=symbol,
                observation_time=ts.to_pydatetime(),
                available_at=_available_at(ts, frequency),
                as_of=as_of or datetime(2100, 1, 1),
                value=value, frequency=frequency, unit=inst.unit,
                source_data_version=SOURCE_DATA_VERSION,
                feature_version=inst.feature_version, quality_flag=flag))
    return points


def get_features(symbol: str, frequency: str, observation_time,
                 as_of: datetime | None = None,
                 feature_names: list[str] | None = None) -> dict[str, float | None]:
    """读取某 observation_time 在 as_of 下的所有 feature 值。"""
    ts = pd.Timestamp(observation_time)
    pts = build_features(symbol, frequency, start=str(ts.date()),
                         end=str(ts.date()), as_of=as_of, feature_names=feature_names)
    return {p.feature_name: p.value for p in pts if p.quality_flag == "OK"}
