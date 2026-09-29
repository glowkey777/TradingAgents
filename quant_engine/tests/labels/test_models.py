# -*- coding: utf-8 -*-
"""Label 模型完整性测试。"""
from quant_engine.labels import LABEL_DEFINITIONS, run_label_pipeline


def test_definitions_complete():
    for d in LABEL_DEFINITIONS.values():
        assert d.label_version, f"{d.label_name} 缺 version"
        assert d.threshold_method == "realized_vol_daily"
        assert d.threshold_multiplier > 0
        assert d.horizon in ("T+1", "T+2")


def test_record_has_lineage():
    out = run_label_pipeline(start="2024-01-01", end="2024-06-03")
    rec = out["T+1"][0]
    assert rec.label_version
    assert rec.source_data_version
    assert rec.feature_cutoff
    assert rec.label in ("UP", "FLAT", "DOWN")
