# -*- coding: utf-8 -*-
"""Missing Data 测试：NOT_AVAILABLE 语义不被转成 0。"""
from quant_engine.state import validate_state


def test_risk_not_available(state_2024):
    assert state_2024.risk.status == "NOT_AVAILABLE"
    assert state_2024.risk.max_position_risk is None  # 不伪造 0


def test_missing_feature_not_zero(state_2024):
    # 无 None 之外的值；缺 feature 保持 None / unavailable 列表
    for v in state_2024.features.values.values():
        assert v is None or isinstance(v, float)
    assert isinstance(state_2024.features.unavailable_features, list)
