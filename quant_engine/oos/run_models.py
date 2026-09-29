# -*- coding: utf-8 -*-
"""Historical PIT Runner 输出模型（P7 STEP 6.2）。

HistoricalRunResult + PITAuditRecord。run_id 完全 deterministic
（禁止 datetime.now()/random UUID）。
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

from .contract import OOS_CONTRACT_VERSION


class RunStatus(str, Enum):
    PASS = "PASS"
    INVALID_TRADING_DATE = "INVALID_TRADING_DATE"
    PIT_VIOLATION = "PIT_VIOLATION"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INVALID = "INVALID"


class PITAuditRecord(BaseModel):
    """机器可审计的 PIT 信息（不只是一个 pit=True）。"""
    pit_check_status: str = "PASS"          # PASS / VIOLATION
    max_observation_time: datetime | None = None
    max_available_at: datetime | None = None
    max_revision_time: datetime | None = None
    prediction_as_of: datetime
    future_rows_detected: int = 0
    revision_rows_detected: int = 0


class HistoricalRunResult(BaseModel):
    """历史 T 的 PIT-safe 重建结果。"""
    run_id: str
    symbol: str = Field(min_length=1)
    prediction_date: date
    prediction_as_of: datetime
    horizon: str = "T+1"
    status: RunStatus
    quant_state: dict | None = None           # QuantState.model_dump()（避免嵌套引用）
    quant_context: str = ""
    p4_regime: dict | None = None             # regime_snapshot
    p5_probability: dict | None = None        # {t1: {...}, t2: {...}}
    quant_state_version: str = ""
    renderer_version: str = ""
    oos_contract_version: str = OOS_CONTRACT_VERSION
    source_lineage: dict | None = None
    pit_audit: PITAuditRecord | None = None


def build_run_id(symbol: str, prediction_date: date, horizon: str,
                 contract_version: str = OOS_CONTRACT_VERSION) -> str:
    """deterministic run identity（symbol+T+horizon+contract_version 唯一确定）。"""
    return f"{symbol}-{prediction_date.isoformat()}-{horizon}-oos-run-{contract_version}"
