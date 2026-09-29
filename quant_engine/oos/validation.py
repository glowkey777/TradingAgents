# -*- coding: utf-8 -*-
"""OOS Contract 验证逻辑（P7 STEP 6.1）。

确定性验证：PIT boundary / trading-day / revision / evaluation_id determinism /
label-prediction 分离。只定义规则，不运行历史批量。
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from quant_engine.data.calendar import TradingCalendar

from .models import DataStatus, Horizon, build_evaluation_id
from .contract import OOS_CONTRACT_VERSION


# ── 1. Trading-day：T+n 按真实交易日 ──
def t_plus_n(calendar: TradingCalendar, t: date, n: int) -> date:
    """返回 T 之后第 n 个真实交易日（禁止 calendar day +1）。"""
    cursor = t
    for _ in range(n):
        cursor = calendar.next_session(cursor)
    return cursor


# ── 2. PIT boundary ──
def is_pit_eligible(available_at: datetime, prediction_as_of: datetime) -> bool:
    """available_at <= prediction_as_of → eligible。"""
    return pd.Timestamp(available_at) <= pd.Timestamp(prediction_as_of)


def is_revision_forbidden(revision_time, prediction_as_of: datetime) -> bool:
    """revision_time > prediction_as_of → 未来修订值，禁止使用。"""
    if revision_time is None:
        return False
    ts = pd.Timestamp(revision_time)
    if pd.isna(ts):
        return False
    return ts > pd.Timestamp(prediction_as_of)


# ── 3. Label / prediction 分离 ──
def label_prediction_boundary_violation(label_uses_outcome_data: bool) -> bool:
    """label 使用未来数据是允许的（仅进入 evaluation label）；
    本函数标记 outcome data 是否被错误用于 prediction。若 True → PIT_VIOLATION。"""
    return label_uses_outcome_data


# ── 4. missing data 分类 ──
def classify_outcome(actual_return: float | None, label: str | None,
                     pit_violated: bool = False) -> DataStatus:
    """outcome 状态分类：禁止 None → 0/neutral/average。"""
    if pit_violated:
        return DataStatus.PIT_VIOLATION
    if label is None or actual_return is None:
        return DataStatus.NOT_EVALUABLE
    if label not in ("UP", "FLAT", "DOWN"):
        return DataStatus.INVALID
    return DataStatus.VALID


# ── 5. evaluation_id determinism ──
def evaluation_id_is_deterministic(symbol: str, prediction_date: date,
                                   horizon: Horizon, n_trials: int = 5) -> bool:
    """重复调用必须产生相同 evaluation_id。"""
    ids = {build_evaluation_id(symbol, prediction_date, horizon) for _ in range(n_trials)}
    return len(ids) == 1


# ── 6. probability source guard ──
def probability_from_p5_only(provenance_source: str) -> bool:
    """概率必须来自 P5；拒绝 LLM/manual/second engine。"""
    return provenance_source == "P5"
