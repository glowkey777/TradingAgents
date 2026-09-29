# -*- coding: utf-8 -*-
"""独立 Availability Auditor（P7 STEP 6.5B 第 10 节）。

不信任 source 自声称 PROVEN。available_at > as_of 即使 source 声称 PROVEN → VIOLATION → FAIL。
"""
from __future__ import annotations

from .availability_models import AvailabilityEvidence, AvailabilityStatus


def audit_availability(evidence: AvailabilityEvidence) -> str:
    """对单条 AvailabilityEvidence 独立审计。

    返回 SAFE / BLOCKED / UNSAFE / FAIL / UNKNOWN。

    独立性核心：优先看 available_at（事实字段），不信任 status（source 声称）。
    - available_at 非 None 且 <= as_of → SAFE（即使 source 声称 UNVERIFIABLE/VIOLATION）
    - available_at 非 None 且 > as_of  → FAIL（即使 source 声称 PROVEN）
    - available_at 是 None：
        VIOLATION    → UNSAFE
        UNVERIFIABLE → BLOCKED
        PROVEN       → BLOCKED（声称 PROVEN 却无 available_at，矛盾）
    """
    # 先看事实字段 available_at，不看 status 声称
    if evidence.available_at is not None:
        if evidence.available_at <= evidence.as_of:
            return "SAFE"          # 事实：available_at <= T
        # available_at > T（未来信息）
        if evidence.status == AvailabilityStatus.VIOLATION:
            return "UNSAFE"        # source 诚实标记了未来 → UNSAFE
        return "FAIL"              # source 声称 PROVEN 但事实未来 → 撒谎 → FAIL
    # available_at 无法建立 → 依 status 保守判定
    if evidence.status == AvailabilityStatus.VIOLATION:
        return "UNSAFE"
    if evidence.status == AvailabilityStatus.UNVERIFIABLE:
        return "BLOCKED"
    if evidence.status == AvailabilityStatus.PROVEN:
        return "BLOCKED"           # 声称 PROVEN 却无 available_at → 矛盾，按 UNVERIFIABLE
    return "UNKNOWN"


def audit_evidence_list(evidences: list[AvailabilityEvidence]) -> str:
    """对一组 evidence 聚合。FAIL > BLOCKED > SAFE（fail-closed）。

    对应 L5 aggregation（用户第 15 节）：
    - 任一 FAIL（VIOLATION 或 available_at > as_of）→ FAIL
    - 任一 BLOCKED（UNVERIFIABLE）→ BLOCKED
    - 全 SAFE → SAFE
    """
    results = [audit_availability(e) for e in evidences]
    if "FAIL" in results or "UNSAFE" in results:
        return "FAIL"
    if "BLOCKED" in results:
        return "BLOCKED"
    return "SAFE"
