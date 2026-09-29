# -*- coding: utf-8 -*-
"""OOS Evaluation Contract 强类型模型（P7 STEP 6.1）。

只定义 contract 类型，不运行计算。evaluation_id 完全 deterministic。
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .contract import OOS_CONTRACT_VERSION

TOLERANCE = 1e-6


class Horizon(str, Enum):
    T1 = "T+1"
    T2 = "T+2"


class DirectionalBias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class DataStatus(str, Enum):
    VALID = "VALID"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    PIT_VIOLATION = "PIT_VIOLATION"
    INVALID = "INVALID"


class LeakageType(str, Enum):
    L1_TEMPORAL = "L1_temporal"
    L2_REVISION = "L2_revision"
    L3_LABEL = "L3_label"
    L4_CROSS_SAMPLE = "L4_cross_sample"
    L5_AGENT_RESEARCH = "L5_agent_research"
    L6_QUANTSTATE = "L6_quantstate"
    L7_CONTEXT = "L7_context"
    L8_THESIS = "L8_thesis"
    L9_TUNING = "L9_tuning"


class ModelProvenanceRef(BaseModel):
    """PredictionRecord 中的 provenance 引用（record 必须记录，供审计）。"""
    model_config = {"frozen": True}
    provider: str
    model: str
    temperature: float | None = None
    prompt_version: str
    agent_version: str
    run_id: str


class EvaluationUnit(BaseModel):
    """一个 OOS evaluation sample 的唯一身份（deterministic）。"""
    model_config = {"frozen": True}
    evaluation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    prediction_date: date                    # T
    prediction_as_of: datetime               # 正式 cutoff（T 收盘后）
    horizon: Horizon
    label_version: str                       # P3 frozen
    quant_state_version: str                 # P6 frozen
    renderer_version: str                    # P7 frozen
    thesis_contract_version: str             # P7 frozen
    contract_version: str = OOS_CONTRACT_VERSION


class PredictionRecord(BaseModel):
    """T 时刻产生的预测（概率必须来自 P5，禁止 LLM/manual/second engine）。"""
    model_config = {"frozen": True}
    prediction_date: date
    symbol: str = Field(min_length=1)
    horizon: Horizon
    p_up: float
    p_flat: float
    p_down: float
    directional_bias: DirectionalBias
    confidence: float = Field(ge=0.0, le=1.0)
    thesis_id: str
    run_id: str
    quant_state_version: str
    renderer_version: str
    model_provenance: ModelProvenanceRef

    @model_validator(mode="after")
    def _check_probability_sum(self):
        s = self.p_up + self.p_flat + self.p_down
        if abs(s - 1.0) > TOLERANCE:
            raise ValueError(f"probability sum={s} != 1（OOS 概率必须来自 P5 且和为 1）")
        for name in ("p_up", "p_flat", "p_down"):
            v = getattr(self, name)
            if not (-TOLERANCE <= v <= 1 + TOLERANCE):
                raise ValueError(f"{name}={v} 越界 [0,1]")
        return self


class OutcomeRecord(BaseModel):
    """T+1/T+2 实际结果（只能进入 evaluation label，禁止进入 prediction pipeline）。"""
    model_config = {"frozen": True}
    evaluation_id: str
    symbol: str
    horizon: Horizon
    actual_return: float | None = None      # close[T+n]/close[T] - 1
    label: str | None = None                # UP / FLAT / DOWN
    label_version: str = "v1"
    outcome_status: DataStatus = DataStatus.VALID   # NOT_EVALUABLE 等


class OOSContract(BaseModel):
    """整体 contract 对象（versioned；historical results 必须记录 contract version）。"""
    model_config = {"frozen": True}
    contract_name: str = "OOS Evaluation Contract"
    contract_version: str = OOS_CONTRACT_VERSION
    symbol: str = "SPY"
    prediction_as_of_rule: str
    prediction_as_of_class: str
    temporal_split: dict
    primary_metrics: tuple[str, ...]
    secondary_metrics: tuple[str, ...]
    baselines: tuple[str, ...]
    leakage_taxonomy: tuple[str, ...]
    missing_data_statuses: tuple[str, ...]


def build_evaluation_id(symbol: str, prediction_date: date, horizon: Horizon,
                        contract_version: str = OOS_CONTRACT_VERSION) -> str:
    """deterministic evaluation_id：symbol + T + horizon + contract_version 唯一确定。"""
    return f"{symbol}-{prediction_date.isoformat()}-{horizon.value}-oos-{contract_version}"
