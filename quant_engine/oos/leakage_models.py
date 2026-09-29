# -*- coding: utf-8 -*-
"""OOS Leakage Audit 模型（P7 STEP 6.4）。

独立于 Builder 的泄漏审计结果。audit_id 完全 deterministic。
NOT_VERIFIED ≠ PASS；FAIL = 发现泄漏。
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

from .contract import OOS_CONTRACT_VERSION
from .models import Horizon

AUDIT_VERSION = "6.4-v1"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_VERIFIED = "NOT_VERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Violation(BaseModel):
    leakage_type: str                 # L1_TEMPORAL / L2_REVISION / ...
    field: str
    description: str
    evidence: dict | None = None


class AuditCheck(BaseModel):
    name: str                         # "L1 Temporal" ...
    status: CheckStatus
    evidence: dict | None = None


class OOSLeakageAuditResult(BaseModel):
    audit_id: str
    prediction_id: str
    symbol: str
    prediction_date: date
    prediction_as_of: datetime
    horizon: Horizon
    overall_status: CheckStatus       # PASS / FAIL / NOT_VERIFIED
    violations: list[Violation] = []
    checks: list[AuditCheck] = []
    oos_contract_version: str = OOS_CONTRACT_VERSION
    quant_state_version: str = ""
    renderer_version: str = ""
    source_lineage: dict | None = None
    audit_version: str = AUDIT_VERSION


def build_audit_id(prediction_id: str, audit_version: str = AUDIT_VERSION) -> str:
    """deterministic audit_id。"""
    return hashlib.sha256(f"leakage|{prediction_id}|{audit_version}".encode("utf-8")).hexdigest()


def overall_status_from_checks(checks: list[AuditCheck]) -> CheckStatus:
    """FAIL 优先；否则 NOT_VERIFIED；全 PASS 才 PASS。"""
    if any(c.status == CheckStatus.FAIL for c in checks):
        return CheckStatus.FAIL
    if any(c.status == CheckStatus.NOT_VERIFIED for c in checks):
        return CheckStatus.NOT_VERIFIED
    return CheckStatus.PASS
