# -*- coding: utf-8 -*-
"""L5 Agent Research Runtime OOS Leakage Audit（P7 STEP 6.5）。

基于 Tool Inventory 判定 L5 PASS/BLOCKED。核心规则：
- LEAKAGE_RISK / CURRENT_ONLY → BLOCKED（发现无 cutoff 的泄漏路径）
- HISTORICAL_BUT_UNVERIFIED → 诚实记录 unverifiable（有 cutoff 但非精确 public availability）
- 全部 PIT_SAFE → PASS
LLM_PARAMETRIC_KNOWLEDGE = OUT_OF_SCOPE（第 13 节明确）。
"""
from __future__ import annotations

from .l5_models import (
    AgentLeakageAuditResult, L5Violation, ViolationType, ToolLeakageStatus,
    build_l5_audit_id,
)
from .l5_tool_inventory import build_tool_inventory


def audit_l5(prediction_id: str, as_of: str) -> AgentLeakageAuditResult:
    """对 12 个 agent tool 的 runtime cutoff + availability 语义做 L5 审计。"""
    inventory = build_tool_inventory()
    violations: list[L5Violation] = []
    blocked_tools: list[str] = []
    unverifiable: list[str] = []

    for entry in inventory:
        status = entry.leakage_status
        if status == ToolLeakageStatus.LEAKAGE_RISK:
            violations.append(L5Violation(
                violation_type=ViolationType.NO_CUTOFF,
                tool=entry.tool_name,
                description=f"{entry.tool_name} 无 cutoff 机制，可能泄漏未来数据",
            ))
        elif status == ToolLeakageStatus.CURRENT_ONLY:
            violations.append(L5Violation(
                violation_type=ViolationType.CURRENT_SEARCH,
                tool=entry.tool_name,
                description=f"{entry.tool_name} 只能返回 current/latest，无法 historical as_of",
            ))
        elif status in (ToolLeakageStatus.UNVERIFIABLE,
                        ToolLeakageStatus.HISTORICAL_BUT_UNVERIFIED):
            # fail-closed：UNVERIFIABLE ≠ SAFE，无法证明 available_at <= T → BLOCKED
            blocked_tools.append(entry.tool_name)
            unverifiable.append(f"{entry.tool_name}（{entry.availability_semantics}）")
            violations.append(L5Violation(
                violation_type=ViolationType.UNVERIFIABLE_AVAILABILITY,
                tool=entry.tool_name,
                description=f"{entry.tool_name} availability 无法证明：{entry.availability_semantics}",
                evidence={
                    "availability_field": entry.availability_field,
                    "historical_availability_proven": entry.historical_availability_proven,
                },
            ))

    # fail-closed 聚合（用户第 7 节）：UNSAFE→FAIL，UNVERIFIABLE→BLOCKED，全 PIT_SAFE→PASS
    unsafe = [v for v in violations
              if v.violation_type in (ViolationType.NO_CUTOFF,
                                      ViolationType.CURRENT_SEARCH)]
    if unsafe:
        overall = "FAIL"
    elif blocked_tools:
        overall = "BLOCKED"
    else:
        overall = "PASS"

    return AgentLeakageAuditResult(
        audit_id=build_l5_audit_id(prediction_id),
        prediction_id=prediction_id,
        as_of=as_of,
        status=overall,
        tool_inventory=inventory,
        violations=violations,
        blocked_tools=blocked_tools,
        unverifiable=unverifiable,
    )
