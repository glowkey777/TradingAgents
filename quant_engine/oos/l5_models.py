# -*- coding: utf-8 -*-
"""L5 Agent Research Runtime OOS Leakage Audit 模型（P7 STEP 6.5）。

只解决 STEP 6.4 留下的 L5 缺口。audit_id deterministic。
"""
from __future__ import annotations

import hashlib
from enum import Enum

from pydantic import BaseModel, Field

L5_AUDIT_VERSION = "6.5-v1"


class ViolationType(str, Enum):
    FUTURE_OBSERVATION = "FUTURE_OBSERVATION"
    FUTURE_PUBLICATION = "FUTURE_PUBLICATION"
    FUTURE_REVISION = "FUTURE_REVISION"
    NO_CUTOFF = "NO_CUTOFF"
    UNVERIFIABLE_AVAILABILITY = "UNVERIFIABLE_AVAILABILITY"
    CURRENT_SEARCH = "CURRENT_SEARCH"
    CACHE_LEAK = "CACHE_LEAK"
    UNKNOWN = "UNKNOWN"


class ToolLeakageStatus(str, Enum):
    PIT_SAFE = "PIT_SAFE"
    CURRENT_ONLY = "CURRENT_ONLY"
    HISTORICAL_BUT_UNVERIFIED = "HISTORICAL_BUT_UNVERIFIED"
    UNVERIFIABLE = "UNVERIFIABLE"
    LEAKAGE_RISK = "LEAKAGE_RISK"


class ToolInventoryEntry(BaseModel):
    """一个 agent tool 的 L5 清单条目（含 availability 语义字段）。"""
    tool_name: str
    data_source: str
    input_date_controls: str              # trade_date / as_of / as_of_window
    historical_cutoff_mechanism: str      # 具体过滤机制（Date/pub_date/period_end/realtime/withhold）
    availability_field: str = "None"      # filed / pub_date / created_at / None
    availability_semantics: str = "None"  # 该字段是否证明 available_at <= T
    filing_field: str = "None"            # filed / None
    publication_field: str = "None"       # pub_date / None
    revision_field: str = "None"          # revision_time / None
    historical_availability_proven: bool = False
    pit_safe: bool
    leakage_status: ToolLeakageStatus
    evidence: str


class L5Violation(BaseModel):
    violation_type: ViolationType
    tool: str
    description: str
    evidence: dict | None = None


class AgentLeakageAuditResult(BaseModel):
    audit_id: str
    prediction_id: str
    as_of: str                        # cutoff（prediction_as_of）
    status: str                       # PASS / BLOCKED / FAIL
    tool_inventory: list[ToolInventoryEntry] = []
    violations: list[L5Violation] = []
    blocked_tools: list[str] = []     # UNVERIFIABLE 的 tool（fail-closed）
    unverifiable: list[str] = []      # 诚实记录 UNVERIFIABLE 接口
    llm_parametric_knowledge: str = "OUT_OF_SCOPE"
    audit_version: str = L5_AUDIT_VERSION


def build_l5_audit_id(prediction_id: str, audit_version: str = L5_AUDIT_VERSION) -> str:
    return hashlib.sha256(f"l5|{prediction_id}|{audit_version}".encode("utf-8")).hexdigest()
