# -*- coding: utf-8 -*-
"""Historical Availability Contract 数据模型（P7 STEP 6.5B）。

AvailabilityEvidence：frozen + deterministic 序列化。
period_end 与 available_at 语义完全独立（用户第 5 节）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AvailabilityStatus(str, Enum):
    PROVEN = "PROVEN"            # available_at 已建立且 <= as_of
    UNVERIFIABLE = "UNVERIFIABLE"  # available_at 无法建立
    VIOLATION = "VIOLATION"      # available_at > as_of（未来信息）


class SourceStatus(str, Enum):
    PIT_SAFE = "PIT_SAFE"
    UNVERIFIABLE = "UNVERIFIABLE"
    UNSAFE = "UNSAFE"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class AvailabilityEvidence(BaseModel):
    """一条 record 的 historical availability 证据（frozen）。"""
    model_config = ConfigDict(frozen=True)

    status: AvailabilityStatus
    available_at: datetime | None = None
    source: str                          # yfinance / alpha_vantage / sec_edgar / fred ...
    source_field: str | None = None      # filed / pub_date / created_at / None
    record_id: str                       # deterministic record 标识
    as_of: datetime                      # prediction cutoff（T）
    reason: str

    def model_dump_json(self, **kwargs) -> str:  # deterministic 序列化（ISO 时间）
        kwargs.setdefault("indent", 2)
        return super().model_dump_json(**kwargs)


class SourceCapability(BaseModel):
    """一个 vendor×tool 的 source capability 矩阵条目。"""
    model_config = ConfigDict(frozen=True)

    source: str
    vendor: str
    tool: str
    dataset: str
    period_field: str | None          # period_end / fiscalDateEnding / end
    publication_field: str | None     # pub_date / created_at
    filing_field: str | None          # filed
    availability_field: str | None    # 能证明 available_at 的字段
    revision_field: str | None        # revision_time
    historical_support: bool
    pit_guarantee: str                # 是否 formal vendor guarantee
    coverage: str
    limitations: str
    status: SourceStatus


def utc_iso(s: str) -> datetime:
    """把 YYYY-MM-DD 归一为 UTC 日期（deterministic）。"""
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
