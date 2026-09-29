# -*- coding: utf-8 -*-
"""Label Definitions：T+1 / T+2 三分类 + dynamic threshold。"""
from __future__ import annotations

from .models import LabelDefinition

T1 = LabelDefinition(
    label_name="t1_up_flat_down", horizon="T+1",
    threshold_method="realized_vol_daily", threshold_multiplier=0.5, label_version="v1",
)
T2 = LabelDefinition(
    label_name="t2_up_flat_down", horizon="T+2",
    threshold_method="realized_vol_daily", threshold_multiplier=0.5, label_version="v1",
)

LABEL_DEFINITIONS = {d.label_name: d for d in (T1, T2)}
