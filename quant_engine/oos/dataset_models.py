# -*- coding: utf-8 -*-
"""OOS Prediction Dataset 模型（P7 STEP 6.3）。

PredictionRecord（dataset 层，扩展 6.1 的 identity/status 字段）+
PredictionDataset + DatasetManifest。prediction_id 完全 deterministic。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .contract import OOS_CONTRACT_VERSION
from .models import DirectionalBias, Horizon, ModelProvenanceRef, TOLERANCE


class RecordStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    PIT_VIOLATION = "PIT_VIOLATION"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


# 禁止进入 prediction-side dataset 的 outcome 字段（schema-level guard）
FORBIDDEN_OUTCOME_FIELDS = (
    "future_close", "future_return", "realized_return", "label", "actual_direction",
    "outcome", "actual", "realized", "t_plus_1_price", "t_plus_2_price",
    "next_close", "next_return",
)


def build_prediction_id(symbol: str, prediction_date: date, prediction_as_of: datetime,
                        horizon: Horizon, contract_version: str = OOS_CONTRACT_VERSION) -> str:
    """deterministic prediction_id（主键）：sha256(symbol|date|as_of|horizon|version)。"""
    key = "|".join([
        symbol, prediction_date.isoformat(), prediction_as_of.isoformat(),
        horizon.value, contract_version,
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class PredictionRecord(BaseModel):
    """一条 prediction record = symbol × prediction_date × horizon。

    概率必须来自 P5（exact-source）；禁止 LLM/manual/second engine 概率。
    outcome 字段完全排除。record_status=PIT_VIOLATION 时 fail-closed（保留 audit）。
    """
    model_config = {"frozen": True}

    # ── identity ──
    prediction_id: str
    run_id: str
    # ── prediction-time identity ──
    symbol: str = Field(min_length=1)
    prediction_date: date
    prediction_as_of: datetime
    horizon: Horizon
    # ── probability（P5 exact-source）──
    p_up: float
    p_flat: float
    p_down: float
    directional_bias: DirectionalBias | None = None
    confidence: float | None = None
    confidence_level: str | None = None
    # ── thesis / run linkage（6.5 填充）──
    thesis_id: str | None = None
    # ── versions ──
    quant_state_version: str
    renderer_version: str
    oos_contract_version: str = OOS_CONTRACT_VERSION
    # ── provenance ──
    model_provenance: ModelProvenanceRef | None = None
    source_lineage: dict | None = None
    # ── status ──
    pit_status: str = "PASS"
    record_status: RecordStatus = RecordStatus.VALID
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _check_probability_sum(self):
        if self.record_status != RecordStatus.VALID:
            return self  # 非 VALID 状态概率为占位 0/0/0，不检查 sum
        s = self.p_up + self.p_flat + self.p_down
        if abs(s - 1.0) > TOLERANCE:
            raise ValueError(f"probability sum={s} != 1（概率必须来自 P5 且和为 1）")
        for name in ("p_up", "p_flat", "p_down"):
            v = getattr(self, name)
            if not (-TOLERANCE <= v <= 1 + TOLERANCE):
                raise ValueError(f"{name}={v} 越界 [0,1]")
        return self


class DatasetManifest(BaseModel):
    """machine-readable manifest（created_at 不影响 dataset identity）。"""
    dataset_version: str
    oos_contract_version: str = OOS_CONTRACT_VERSION
    symbol_scope: list[str]
    start_date: date | None = None
    end_date: date | None = None
    horizons: list[str]
    expected_count: int = 0
    valid_count: int = 0
    rejected_count: int = 0
    not_available_count: int = 0
    pit_violation_count: int = 0
    quant_state_version: str = ""
    renderer_version: str = ""
    builder_version: str
    schema_hash: str = ""
    dataset_hash: str = ""
    manifest_hash: str = ""
    created_at: str = ""


class PredictionDataset(BaseModel):
    """prediction-side only dataset。禁止含 outcome 字段。"""
    dataset_version: str
    records: list[PredictionRecord]
    manifest: DatasetManifest


def _sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def compute_schema_hash() -> str:
    """schema_hash：字段名列表（sorted）的 sha256，不含数据值。"""
    fields = sorted(PredictionRecord.model_fields.keys())
    return _sha256({"fields": fields})


def compute_dataset_hash(records: list[PredictionRecord]) -> str:
    """dataset_hash：records（deterministic 排序 + 序列化）的 sha256，不含 created_at。"""
    payload = [r.model_dump(mode="json") for r in records]
    return _sha256(payload)
