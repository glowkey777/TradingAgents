# -*- coding: utf-8 -*-
"""QuantState Contract：强类型、immutable、可序列化的市场状态对象。

复用 P4 RegimeState / P5 ProbabilityEstimate，不为统一接口反向改冻结模块。
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from quant_engine.regimes.models import RegimeState
from quant_engine.probability.models import ProbabilityEstimate

SCHEMA_VERSION = "quant-state-schema-v1"
STATE_VERSION = "quant-state-v1.0.0"


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    trading_date: date
    frequency: str = "daily"


class FeatureSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    feature_version: str
    values: dict[str, float | None]
    available_features: list[str]
    unavailable_features: list[str]


class EventOccurrence(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_name: str
    event_time: datetime
    event_value: float | None = None
    threshold: float | None = None
    event_version: str = "v1"
    available_at: datetime


class EventSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_version: str
    active_events: list[EventOccurrence]
    detected_events: list[EventOccurrence]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str
    method: str
    sample_size: int
    status: str                          # VALID / LOW_SAMPLE / INSUFFICIENT_SAMPLE / NOT_AVAILABLE
    version: str
    horizon: str | None = None


class EvidenceSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_evidence: list[EvidenceItem]
    probability_evidence: list[EvidenceItem]


class ProbabilitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    probability_version: str
    t1: ProbabilityEstimate | None = None
    t2: ProbabilityEstimate | None = None


class RiskSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str = "NOT_AVAILABLE"        # NOT_AVAILABLE（Risk Engine 未实现）
    max_position_risk: float | None = None
    max_loss: float | None = None
    volatility_state: str | None = None
    risk_flags: list[str] = []
    risk_version: str = "v0"


class DataQuality(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str                          # VALID / PARTIAL / INSUFFICIENT_DATA / INVALID
    missing_features: list[str] = []
    missing_events: list[str] = []
    missing_macro: list[str] = []
    insufficient_sample_items: list[str] = []
    pit_validated: bool = True
    validation_version: str = "v1"


class StateConfidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    score: float | None = None
    level: str = "NOT_AVAILABLE"         # HIGH / MEDIUM / LOW / NOT_AVAILABLE
    reasons: list[str] = []
    method: str = "data_completeness"
    version: str = "v1"


class StateLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    data_versions: dict[str, str]
    feature_version: str
    event_version: str
    regime_version: str
    probability_version: str
    risk_version: str
    label_version: str | None = None
    source_versions: dict[str, str]
    pipeline_version: str


class QuantState(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_VERSION
    state_version: str = STATE_VERSION

    symbol: str
    as_of: datetime

    market: MarketSnapshot
    features: FeatureSnapshot
    events: EventSnapshot
    evidence: EvidenceSnapshot
    regime: RegimeState
    probability: ProbabilitySnapshot
    risk: RiskSnapshot

    data_quality: DataQuality
    confidence: StateConfidence
    lineage: StateLineage

    created_at: datetime
