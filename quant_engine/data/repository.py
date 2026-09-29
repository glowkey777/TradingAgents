# -*- coding: utf-8 -*-
"""Canonical Parquet Repository + PIT 读取。

Canonical = 未复权价（OpenD 主源）。CSV 复权价不进 canonical 库（隔离）。
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .models import MarketDataPoint

try:
    import pyarrow  # noqa: F401
    _HAS_PYARROW = True
except ImportError:
    _HAS_PYARROW = False


def _points_to_df(points: list[MarketDataPoint]) -> pd.DataFrame:
    return pd.DataFrame([p.model_dump() for p in points])


def _df_to_points(df: pd.DataFrame) -> list[MarketDataPoint]:
    return [MarketDataPoint(**row) for row in df.to_dict(orient="records")]


class ParquetRepository:
    def __init__(self, dir_path: str):
        self.dir = Path(dir_path)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, dataset_name: str) -> Path:
        return self.dir / f"{dataset_name}.parquet"

    def write(self, dataset_name: str, points: list[MarketDataPoint]) -> None:
        df = _points_to_df(points)
        if _HAS_PYARROW:
            df.to_parquet(self._path(dataset_name), index=False)
        else:
            df.to_pickle(self._path(dataset_name).with_suffix(".pkl"))

    def load(self, dataset_name: str) -> list[MarketDataPoint]:
        path = self._path(dataset_name)
        if path.exists():
            return _df_to_points(pd.read_parquet(path))
        pkl = path.with_suffix(".pkl")
        if pkl.exists():
            return _df_to_points(pd.read_pickle(pkl))
        return []

    # ---- PIT 读取 ----
    def get(self, symbol: str, field: str, observation_date: date,
            as_of: datetime, dataset_name: str) -> MarketDataPoint | None:
        rows = [p for p in self.load(dataset_name)
                if p.symbol == symbol and p.field == field
                and p.observation_time.date() == observation_date
                and p.visible_at(as_of)]
        return rows[-1] if rows else None

    def get_history(self, symbol: str, field: str, start: date, end: date,
                    as_of: datetime, dataset_name: str) -> list[MarketDataPoint]:
        return [p for p in self.load(dataset_name)
                if p.symbol == symbol and p.field == field
                and start <= p.observation_time.date() <= end
                and p.visible_at(as_of)]

    def latest(self, symbol: str, field: str, as_of: datetime,
               dataset_name: str) -> MarketDataPoint | None:
        rows = [p for p in self.load(dataset_name)
                if p.symbol == symbol and p.field == field and p.visible_at(as_of)]
        return max(rows, key=lambda p: p.observation_time) if rows else None
