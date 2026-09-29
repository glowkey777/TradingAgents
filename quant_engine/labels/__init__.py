# -*- coding: utf-8 -*-
"""Label Engine 模块（P3-B）。"""
from .models import LabelDefinition, LabelRecord
from .definitions import LABEL_DEFINITIONS
from .generator import generate_labels
from .validation import test_C_label_not_in_feature_registry, test_D_future_endpoint_missing_makes_unavailable
from .pipeline import run_label_pipeline

__all__ = [
    "LabelDefinition", "LabelRecord", "LABEL_DEFINITIONS",
    "generate_labels", "run_label_pipeline",
    "test_C_label_not_in_feature_registry", "test_D_future_endpoint_missing_makes_unavailable",
]
