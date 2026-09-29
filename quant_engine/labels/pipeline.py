# -*- coding: utf-8 -*-
"""Label Pipeline：生成 T+1/T+2 labels。"""
from __future__ import annotations

from .definitions import LABEL_DEFINITIONS
from .generator import generate_labels


def run_label_pipeline(symbol: str = "SPY", start: str = "2013-01-01",
                       end: str = "2026-09-25") -> dict:
    """生成 T+1/T+2 label 数据集。"""
    out = {}
    for name, d in LABEL_DEFINITIONS.items():
        out[d.horizon] = generate_labels(symbol, d, start, end)
    return out
