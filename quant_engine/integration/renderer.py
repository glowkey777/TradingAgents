# -*- coding: utf-8 -*-
"""QuantState Renderer：typed QuantState → deterministic LLM/human-readable text。

versioned、PIT-safe、loss-aware。只做事实呈现，不加入 prediction/opinion/recommendation。
"""
from __future__ import annotations

from quant_engine.state.models import QuantState

RENDERER_VERSION = "quant_context_v1"


def _f(v) -> str:
    """float → 定长字符串；None → NOT_AVAILABLE（不转 0）。"""
    if v is None:
        return "NOT_AVAILABLE"
    return f"{v:.4f}"


def _dict_lines(d: dict, indent: int = 2) -> list[str]:
    out = []
    pad = " " * indent
    for k in sorted(d.keys()):  # sorted 保证 deterministic
        out.append(f"{pad}{k}: {_f(d[k])}")
    return out


def render_quant_state(state: QuantState) -> str:
    """QuantState → 确定性文本（quant_context_v1）。"""
    L: list[str] = []
    L.append(f"[QuantContext {RENDERER_VERSION}]")
    L.append(f"Symbol: {state.symbol}")
    L.append(f"As of: {state.as_of.isoformat()}")

    m = state.market
    L.append("")
    L.append("MARKET")
    L.append(f"  trading_date: {m.trading_date.isoformat()}")
    L.append(f"  close: {_f(m.close)}")
    L.append(f"  open: {_f(m.open)}")
    L.append(f"  high: {_f(m.high)}")
    L.append(f"  low: {_f(m.low)}")
    L.append(f"  volume: {_f(m.volume)}")

    L.append("")
    L.append("REGIME")
    for dim, label in (("trend", "Trend"), ("volatility", "Volatility"),
                       ("macro", "Macro"), ("event", "Event")):
        d = getattr(state.regime, dim)
        L.append(f"  {label}:")
        if d:
            L.extend(_dict_lines(d, 4))
        else:
            L.append("    NOT_AVAILABLE")

    L.append("")
    L.append("PROBABILITY")
    for h in ("t1", "t2"):
        est = getattr(state.probability, h)
        if est is None:
            L.append(f"  {h.upper()}: NOT_AVAILABLE")
            continue
        L.append(f"  {h.upper()}:")
        L.append(f"    UP: {_f(est.p_up)}")
        L.append(f"    FLAT: {_f(est.p_flat)}")
        L.append(f"    DOWN: {_f(est.p_down)}")
        L.append(f"    status: {est.status}")
        L.append(f"    sample_size: {est.sample_size}")
        L.append(f"    evidence_level: {est.evidence_level}")

    L.append("")
    L.append("EVENTS")
    if state.events.active_events:
        for e in state.events.active_events:
            L.append(f"  - {e.event_name} (value: {_f(e.event_value)}, "
                     f"threshold: {_f(e.threshold)})")
    else:
        L.append("  (none)")

    L.append("")
    L.append("EVIDENCE")
    if state.evidence.probability_evidence:
        for e in state.evidence.probability_evidence:
            L.append(f"  - {e.source} {e.method} {e.horizon or ''}: "
                     f"sample_size={e.sample_size}, status={e.status}")
    else:
        L.append("  (none)")

    L.append("")
    L.append("RISK")
    L.append(f"  status: {state.risk.status}")

    L.append("")
    L.append("DATA QUALITY")
    L.append(f"  status: {state.data_quality.status}")
    if state.data_quality.missing_features:
        L.append(f"  missing_features: {len(state.data_quality.missing_features)}")
    if state.data_quality.insufficient_sample_items:
        L.append(f"  insufficient_sample: {', '.join(sorted(state.data_quality.insufficient_sample_items))}")

    L.append("")
    L.append("CONFIDENCE")
    L.append(f"  level: {state.confidence.level}")
    L.append(f"  score: {_f(state.confidence.score)}")

    L.append("")
    L.append("LINEAGE")
    L.append(f"  pipeline_version: {state.lineage.pipeline_version}")
    L.append(f"  feature_version: {state.lineage.feature_version}")
    L.append(f"  regime_version: {state.lineage.regime_version}")
    L.append(f"  probability_version: {state.lineage.probability_version}")

    return "\n".join(L)
