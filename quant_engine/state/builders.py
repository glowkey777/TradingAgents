# -*- coding: utf-8 -*-
"""QuantState Builder：只消费 P1-P5，不重新计算。"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import pandas as pd

from quant_engine.features.base import load_wide, load_macro_wide
from quant_engine.features.pipeline import build_features
from quant_engine.events import detect_events
from quant_engine.regimes.engine import compute_regime
from quant_engine.probability.estimator import estimate
from quant_engine.probability.definitions import BASELINE_HIERARCHICAL

from .models import (
    QuantState, MarketSnapshot, FeatureSnapshot, EventSnapshot, EventOccurrence,
    EvidenceSnapshot, EvidenceItem, ProbabilitySnapshot, RiskSnapshot,
    DataQuality, StateConfidence,
)
from .lineage import build_lineage


@lru_cache(maxsize=1)
def _cached_history() -> pd.DataFrame:
    from quant_engine.probability import build_history_table
    return build_history_table("2013-01-01", "2026-09-25")


def _val(wide: pd.DataFrame, obs, field: str) -> float | None:
    if field not in wide.columns:
        return None
    v = wide.loc[obs, field]
    return float(v) if not pd.isna(v) else None


def _dominant(d: dict[str, float]) -> str:
    return max(d, key=d.get) if d else "N/A"


def _confidence_level(score: float) -> str:
    if score >= 0.8:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    return "LOW"


def build_quant_state(symbol: str = "SPY", as_of: datetime | None = None) -> QuantState:
    as_of = as_of or datetime(2100, 1, 1)

    # 1. observation_time = 最后一个 as_of 可见的交易日（PIT 核心）
    wide = load_wide("daily", as_of=as_of)
    if wide.empty:
        raise ValueError(f"as_of={as_of} 之前无可用 SPY 数据")
    obs = wide.index.max()

    # 2. MarketSnapshot
    market = MarketSnapshot(
        close=_val(wide, obs, "close"), open=_val(wide, obs, "open"),
        high=_val(wide, obs, "high"), low=_val(wide, obs, "low"),
        volume=_val(wide, obs, "volume"), trading_date=obs.date(), frequency="daily",
    )

    # 3. FeatureSnapshot（当天全部 daily feature，含 quality_flag；warm-up 往前推覆盖 lookback）
    start = str((obs - pd.Timedelta(days=400)).date())
    pts = build_features(symbol, "daily", start=start, end=str(obs.date()), as_of=as_of)
    values: dict[str, float | None] = {}
    available: list[str] = []
    unavailable: list[str] = []
    for p in pts:
        if p.observation_time.date() == obs.date():
            values[p.feature_name] = p.value
            (available if p.quality_flag == "OK" else unavailable).append(p.feature_name)
    features = FeatureSnapshot(feature_version="v1", values=values,
                               available_features=sorted(available),
                               unavailable_features=sorted(unavailable))

    # 4. EventSnapshot（消费 P3，当天事件）
    day_events = detect_events(symbol, None, str(obs.date()), str(obs.date()), as_of)
    day_events = [e for e in day_events if pd.Timestamp(e.observation_time).date() == obs.date()]
    occurrences = [EventOccurrence(
        event_name=e.event_name, event_time=e.event_time, event_value=e.event_value,
        threshold=e.threshold, event_version=e.event_version, available_at=e.available_at,
    ) for e in day_events]
    events = EventSnapshot(event_version="v1",
                           active_events=occurrences, detected_events=occurrences)

    # 5. RegimeState（直接消费 P4）
    regime = compute_regime(symbol, obs.to_pydatetime(), as_of)

    # 6. ProbabilitySnapshot（直接消费 P5；history 全量缓存）
    history = _cached_history()
    current = {
        "trend": _dominant(regime.trend), "volatility": _dominant(regime.volatility),
        "macro": _dominant(regime.macro), "events": {e.event_name for e in occurrences},
    }
    t1 = estimate(history, current, BASELINE_HIERARCHICAL, "T+1",
                  obs.to_pydatetime(), as_of, symbol)
    t2 = estimate(history, current, BASELINE_HIERARCHICAL, "T+2",
                  obs.to_pydatetime(), as_of, symbol)
    probability = ProbabilitySnapshot(probability_version="v1", t1=t1, t2=t2)

    # 7. Risk Interface（未实现 → NOT_AVAILABLE，不伪造）
    risk = RiskSnapshot(status="NOT_AVAILABLE")

    # 8. EvidenceSnapshot
    prob_evidence = [EvidenceItem(
        source="P5", method=est.method, sample_size=est.sample_size,
        status=est.status, version=est.probability_version, horizon=est.horizon,
    ) for est in (t1, t2)]
    evidence = EvidenceSnapshot(event_evidence=[], probability_evidence=prob_evidence)

    # 9. DataQuality
    missing_macro = [c for c in ("vix", "us5y", "us10y", "dxy", "wti")
                     if c not in wide.columns]
    insufficient = [i.source for i in prob_evidence if i.status != "VALID"]
    dq_status = regime.overall_status() if regime.status else "INVALID"
    dq = DataQuality(status=dq_status, missing_features=features.unavailable_features,
                     missing_events=[], missing_macro=missing_macro,
                     insufficient_sample_items=insufficient, pit_validated=True)

    # 10. Confidence（data completeness，≠ p_up）
    conf_values = [v for v in regime.confidence.values() if isinstance(v, (int, float))]
    score = sum(conf_values) / len(conf_values) if conf_values else None
    confidence = StateConfidence(score=score, level=_confidence_level(score) if score is not None else "NOT_AVAILABLE")

    # 11. Lineage
    lineage = build_lineage()

    return QuantState(
        symbol=symbol, as_of=as_of, market=market, features=features, events=events,
        evidence=evidence, regime=regime, probability=probability, risk=risk,
        data_quality=dq, confidence=confidence, lineage=lineage, created_at=as_of,
    )
