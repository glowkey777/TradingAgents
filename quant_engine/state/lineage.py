# -*- coding: utf-8 -*-
"""StateLineage：QuantState 的完整来源追踪。"""
from __future__ import annotations

from .models import StateLineage

DATA_VERSION = "p1_canonical_v1"
FEATURE_VERSION = "v1"
EVENT_VERSION = "v1"
REGIME_VERSION = "v1"
PROBABILITY_VERSION = "v1"
RISK_VERSION = "v0"
LABEL_VERSION = "v1"
PIPELINE_VERSION = "p6_v1"


def build_lineage(data_versions: dict[str, str] | None = None,
                  source_versions: dict[str, str] | None = None) -> StateLineage:
    return StateLineage(
        data_versions=data_versions or {"daily": DATA_VERSION, "macro": DATA_VERSION},
        feature_version=FEATURE_VERSION,
        event_version=EVENT_VERSION,
        regime_version=REGIME_VERSION,
        probability_version=PROBABILITY_VERSION,
        risk_version=RISK_VERSION,
        label_version=LABEL_VERSION,
        source_versions=source_versions or {
            "features": "p2", "events": "p3", "regime": "p4", "probability": "p5"},
        pipeline_version=PIPELINE_VERSION,
    )
