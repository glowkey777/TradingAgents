# -*- coding: utf-8 -*-
"""QuantState Validation：结构 / PIT / 概率和 / 版本 / 缺数据 / lineage。"""
from __future__ import annotations

from .models import QuantState


def validate_state(state: QuantState) -> list[str]:
    errors: list[str] = []

    # structural
    if not state.schema_version:
        errors.append("schema_version 缺失")
    if not state.state_version:
        errors.append("state_version 缺失")
    if not state.symbol:
        errors.append("symbol 缺失")
    if state.as_of is None:
        errors.append("as_of 缺失")

    # PIT：所有 available_at <= as_of
    for e in state.events.active_events:
        if e.available_at > state.as_of:
            errors.append(f"event {e.event_name} available_at={e.available_at} > as_of（PIT 违例）")

    # probability sum = 1
    for name, est in (("t1", state.probability.t1), ("t2", state.probability.t2)):
        if est is None:
            continue
        s = est.p_up + est.p_flat + est.p_down
        if abs(s - 1.0) > 1e-6:
            errors.append(f"probability {name} sum={s} != 1")
        if est.p_up < -1e-6 or est.p_down < -1e-6:
            errors.append(f"probability {name} 出现负值")

    # version 完整
    for field, val in (("feature", state.features.feature_version),
                       ("event", state.events.event_version),
                       ("regime", state.regime.regime_version),
                       ("probability", state.probability.probability_version)):
        if not val:
            errors.append(f"{field} version 缺失")

    # missing data 不得转 0（NOT_AVAILABLE 语义保留）
    if state.risk.status != "NOT_AVAILABLE" and state.risk.max_position_risk == 0:
        errors.append("risk 缺失被转成 0")

    # lineage 完整
    if not state.lineage.pipeline_version or not state.lineage.feature_version:
        errors.append("lineage 不完整")

    return errors
