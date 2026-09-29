# -*- coding: utf-8 -*-
"""Feature 基类 + PIT-safe 数据读取（只读 P1 canonical data）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pandas as pd

from .models import FeatureDefinition
from .registry import FeatureRegistry

INGEST = Path(r"F:\Youtube\0413\TradingAgents\data\ingested")
MACRO_CSV = Path(r"F:\Youtube\stock\spy_macro_2013_2026.csv")
SOURCE_DATA_VERSION = "p1_canonical_v1"


def load_wide(frequency: str, as_of: datetime | None = None) -> pd.DataFrame:
    """从 P1 canonical parquet 只读，转 wide 表（timestamp index × field columns），PIT 过滤。

    frequency: 'daily' | '15m'
    """
    frames = [pd.read_parquet(f) for f in sorted((INGEST / frequency).glob("*.parquet"))]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if as_of is not None:
        avail = pd.to_datetime(df["available_at"])
        df = df[avail <= pd.Timestamp(as_of)]
    wide = df.pivot_table(index="timestamp", columns="field",
                          values="value", aggfunc="last")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def load_macro_wide(as_of: datetime | None = None) -> pd.DataFrame:
    """读宏观 CSV（yfinance 源），转 wide 表，PIT 过滤。"""
    df = pd.read_csv(MACRO_CSV, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    if as_of is not None:
        df = df[df.index <= pd.Timestamp(as_of).normalize() + pd.Timedelta(days=1)]
    return df


class Feature(ABC):
    """Feature 基类。子类定义元数据 + 实现 compute（向量化，无 look-ahead）。"""

    name: str = ""
    definition: str = ""
    formula: str = ""
    input_fields: list[str] = []
    frequency: str = "daily"
    lookback: int | None = None
    unit: str | None = None
    output_type: str = "float"
    feature_version: str = "v1"
    availability_rule: str = "after current observation available"
    pit_rule: str = "inherited from source data"

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """输入 wide 表（含必要字段），输出 feature 序列（index=timestamp）。"""

    def to_definition(self) -> FeatureDefinition:
        return FeatureDefinition(
            feature_name=self.name, definition=self.definition, formula=self.formula,
            input_fields=self.input_fields, frequency=self.frequency, lookback=self.lookback,
            availability_rule=self.availability_rule, pit_rule=self.pit_rule,
            unit=self.unit, output_type=self.output_type, feature_version=self.feature_version,
        )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "name", "") and "compute" in cls.__dict__:
            inst = cls()
            FeatureRegistry.register(inst.to_definition())
            FeatureRegistry.register_instance(cls.name, inst)
