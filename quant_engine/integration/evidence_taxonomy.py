# -*- coding: utf-8 -*-
"""Evidence taxonomy（STEP 5.11 audit-sidecar，不修改 frozen TradingThesis contract）。

现有 EvidenceReference.source_type 是「QuantState 内部数据类型」（feature/event/
regime/probability/risk/market），本 taxonomy 是「证据来源」维度（谁产生了它）。

两个维度正交：QuantState 内部类型 → 证据来源的映射在此定义，供 audit 层分类。
"""
from __future__ import annotations

from enum import Enum


class EvidenceSource(str, Enum):
    """证据来源（谁产生了这条证据）。"""
    QUANT_ENGINE = "quant_engine"          # P2 feature / P3 event / P4 regime / P5 probability
    MARKET_DATA = "market_data"            # QuantState.market（close/open/high/low/volume）
    NEWS = "news"                          # News Analyst 报告
    SENTIMENT = "sentiment"                # Sentiment Analyst 报告
    FUNDAMENTALS = "fundamentals"          # Fundamentals Analyst 报告
    AGENT_INFERENCE = "agent_inference"    # Agent 自己的推理/判断（非 QuantState 事实）
    DEBATE = "debate"                      # Bull/Bear 辩论产物
    RISK = "risk"                          # Risk Debate 产物 / QuantState.risk
    UNKNOWN = "unknown"


# 现有 EvidenceReference.source_type → 证据来源 的映射
SOURCE_TYPE_TO_EVIDENCE_SOURCE: dict[str, EvidenceSource] = {
    "feature": EvidenceSource.QUANT_ENGINE,
    "event": EvidenceSource.QUANT_ENGINE,
    "regime": EvidenceSource.QUANT_ENGINE,
    "probability": EvidenceSource.QUANT_ENGINE,
    "risk": EvidenceSource.RISK,
    "market": EvidenceSource.MARKET_DATA,
}


def classify_source(source_type: str) -> EvidenceSource:
    """现有 source_type → EvidenceSource。未知类型 → UNKNOWN。"""
    return SOURCE_TYPE_TO_EVIDENCE_SOURCE.get(source_type, EvidenceSource.UNKNOWN)


# QuantState 中 NOT_AVAILABLE 的字段（P6 未实现，Agent 不得引用为证据）
# 注意：只用能精确命中的词，避免子串误匹配（如 "positive" 含 "iv"、"negative" 含 "iv"）
NOT_AVAILABLE_FIELDS = ("gamma", "implied_volatility", "implied volatility",
                        "breadth", "put_call", "put/call", "tail_risk")
