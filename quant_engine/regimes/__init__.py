# -*- coding: utf-8 -*-
"""Regime Engine 模块（P4）。"""
from .models import RegimeProbability, RegimeRule, RegimeDefinition, RegimeState, PROBABILITY_TYPE
from .registry import RegimeRegistry
from .scorers import normalize, data_completeness
from .engine import compute_regime
from .pipeline import run_regime_history

# 登记所有维度定义 + 规则（导入即注册）
from . import trend as _trend      # noqa: F401
from . import volatility as _vol   # noqa: F401
from . import macro as _macro      # noqa: F401
from . import event as _event      # noqa: F401

_trend.register()
_vol.register()
_macro.register()
_event.register()

__all__ = [
    "RegimeProbability", "RegimeRule", "RegimeDefinition", "RegimeState",
    "PROBABILITY_TYPE", "RegimeRegistry", "normalize", "data_completeness",
    "compute_regime", "run_regime_history",
]
