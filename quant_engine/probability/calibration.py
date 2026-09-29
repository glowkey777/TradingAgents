# -*- coding: utf-8 -*-
"""Calibration：第一版 Identity（NOT_CALIBRATED）。"""
from __future__ import annotations

from typing import Protocol


class ProbabilityCalibrator(Protocol):
    def transform(self, p_up: float, p_flat: float, p_down: float) -> tuple[float, float, float]:
        ...


class IdentityCalibrator:
    """第一版不校准，概率即原始条件分布估计。"""

    def transform(self, p_up: float, p_flat: float, p_down: float) -> tuple[float, float, float]:
        return p_up, p_flat, p_down
