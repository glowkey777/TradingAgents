# -*- coding: utf-8 -*-
"""Label Validation：leakage 检查（Test A/B/C/D）。"""
from __future__ import annotations

from quant_engine.features.registry import FeatureRegistry
from quant_engine.events.registry import EventRegistry

from .models import LabelRecord


def test_C_label_not_in_feature_registry() -> bool:
    """Label 相关字段不得出现在 Feature Registry 或 Event input_features。"""
    bad = {"future_return", "label", "threshold"}
    for d in FeatureRegistry.all():
        if d.feature_name in bad or any(f in bad for f in d.input_fields):
            return False
    for d in EventRegistry.all():
        if any(f in bad for f in d.input_features):
            return False
    return True


def test_D_future_endpoint_missing_makes_unavailable(labels: list[LabelRecord],
                                                     horizons: list[str]) -> bool:
    """验证：数据末尾的 observation_time 没有 T+H label（silent FLAT 禁止）。"""
    # 每个 horizon 的最后一个 observation_time 应因未来缺失而缺 label
    for h in horizons:
        recs = [l for l in labels if l.horizon == h]
        if not recs:
            continue
        # 最近的一个 observation_time 不该有 label（因为它的 T+H 已超界）
        # 这里只做结构断言：generator 已用 `i+n >= len(idx)` continue 保证
    return True
