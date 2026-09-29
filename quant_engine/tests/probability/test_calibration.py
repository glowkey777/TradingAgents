# -*- coding: utf-8 -*-
"""Calibration 测试。"""
from quant_engine.probability.calibration import IdentityCalibrator


def test_identity_passthrough():
    c = IdentityCalibrator()
    assert c.transform(0.4, 0.3, 0.3) == (0.4, 0.3, 0.3)
