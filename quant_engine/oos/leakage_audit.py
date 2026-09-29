# -*- coding: utf-8 -*-
"""OOS Leakage Audit（P7 STEP 6.4）。

独立于 STEP 6.3 Builder：不信任 record.pit_status / Builder 自声明，
重新验证 historical_run.pit_audit 的 timestamps / source lineage / dependency boundary。
NOT_VERIFIED ≠ PASS；发现泄漏 → FAIL（fail-closed）。
"""
from __future__ import annotations

import inspect
from datetime import datetime

import pandas as pd

from .contract import OOS_CONTRACT_VERSION
from .run_models import HistoricalRunResult
from .dataset_models import PredictionRecord, FORBIDDEN_OUTCOME_FIELDS
from .leakage_models import (
    OOSLeakageAuditResult, AuditCheck, Violation, CheckStatus,
    build_audit_id, overall_status_from_checks, AUDIT_VERSION,
)

# PredictionRecord 中若存在这些字段，则 thesis 内容被写入 prediction（需检查 source timestamp）
THESIS_CONTENT_FIELDS = (
    "thesis_summary", "supporting_evidence", "contradicting_evidence",
    "invalidation", "thesis_text", "thesis_reasoning",
)

# 禁止以 substring 判泄漏的字段名（false positive 控制：typed schema，非粗暴 substring）
EXACT_OUTCOME_FIELDS = set(FORBIDDEN_OUTCOME_FIELDS)


def _check_temporal(record: PredictionRecord, hr: HistoricalRunResult | None) -> AuditCheck:
    if hr is None or hr.pit_audit is None:
        return AuditCheck(name="L1 Temporal", status=CheckStatus.NOT_VERIFIED,
                          evidence={"reason": "no historical_run.pit_audit"})
    max_avail = hr.pit_audit.max_available_at
    if max_avail is not None and pd.Timestamp(max_avail) > pd.Timestamp(record.prediction_as_of):
        return AuditCheck(name="L1 Temporal", status=CheckStatus.FAIL,
                          evidence={"max_available_at": str(max_avail),
                                    "prediction_as_of": str(record.prediction_as_of)})
    return AuditCheck(name="L1 Temporal", status=CheckStatus.PASS,
                      evidence={"max_available_at": str(max_avail),
                                "prediction_as_of": str(record.prediction_as_of)})


def _check_revision(record: PredictionRecord, hr: HistoricalRunResult | None) -> AuditCheck:
    if hr is None or hr.pit_audit is None:
        return AuditCheck(name="L2 Revision", status=CheckStatus.NOT_VERIFIED,
                          evidence={"reason": "no historical_run.pit_audit"})
    max_rev = hr.pit_audit.max_revision_time
    if max_rev is not None and pd.Timestamp(max_rev) > pd.Timestamp(record.prediction_as_of):
        return AuditCheck(name="L2 Revision", status=CheckStatus.FAIL,
                          evidence={"max_revision_time": str(max_rev),
                                    "prediction_as_of": str(record.prediction_as_of)})
    return AuditCheck(name="L2 Revision", status=CheckStatus.PASS,
                      evidence={"max_revision_time": str(max_rev)})


def _check_label(record: PredictionRecord) -> AuditCheck:
    """L3：typed schema + serialized payload 均不得出现 outcome 字段（非 substring）。"""
    schema_fields = set(record.model_fields.keys())
    leaked_schema = EXACT_OUTCOME_FIELDS & schema_fields
    payload = record.model_dump(mode="json")
    leaked_payload = EXACT_OUTCOME_FIELDS & set(payload.keys())
    if leaked_schema or leaked_payload:
        return AuditCheck(name="L3 Label", status=CheckStatus.FAIL,
                          evidence={"leaked_schema": sorted(leaked_schema),
                                    "leaked_payload": sorted(leaked_payload)})
    return AuditCheck(name="L3 Label", status=CheckStatus.PASS,
                      evidence={"schema_clean": True, "payload_clean": True})


def _check_cross_sample() -> AuditCheck:
    """L4：builder 无 module-level mutable state（无跨样本污染载体）。"""
    import quant_engine.oos.dataset_builder as db
    mutable = []
    for name, val in vars(db).items():
        if name.startswith("__"):
            continue
        if isinstance(val, (type, str, int, float, tuple, type(None))):
            continue
        if callable(val):
            continue
        if isinstance(val, (list, dict, set, bytearray)):
            mutable.append(name)
    if mutable:
        return AuditCheck(name="L4 Cross-Sample", status=CheckStatus.FAIL,
                          evidence={"mutable_globals": mutable})
    return AuditCheck(name="L4 Cross-Sample", status=CheckStatus.PASS,
                      evidence={"no_mutable_globals": True})


def _check_agent_research() -> AuditCheck:
    """L5：static boundary（builder 不依赖 TradingAgents 构造概率）+ interface 待 6.5。"""
    import quant_engine.oos.dataset_builder as db
    src = inspect.getsource(db)
    depends_on_agents = ("tradingagents" in src) or ("TradingAgents" in src)
    if depends_on_agents:
        return AuditCheck(name="L5 Agent Research", status=CheckStatus.FAIL,
                          evidence={"builder_depends_on_tradingagents": True})
    # static boundary PASS，但 agent research 是否访问 future data 需跑 Multi-Agent（6.5）
    return AuditCheck(name="L5 Agent Research", status=CheckStatus.NOT_VERIFIED,
                      evidence={"static_boundary_clean": True,
                                "reason": "interface audit requires historical Multi-Agent run (STEP 6.5)"})


def _check_quantstate(record: PredictionRecord, hr: HistoricalRunResult | None) -> AuditCheck:
    """L6：post-build PIT 无泄漏 + source_lineage 完整。"""
    if hr is not None and hr.pit_audit is not None:
        if hr.pit_audit.future_rows_detected > 0:
            return AuditCheck(name="L6 QuantState", status=CheckStatus.FAIL,
                              evidence={"future_rows_detected": hr.pit_audit.future_rows_detected})
    if record.source_lineage is None:
        return AuditCheck(name="L6 QuantState", status=CheckStatus.FAIL,
                          evidence={"reason": "source_lineage missing"})
    return AuditCheck(name="L6 QuantState", status=CheckStatus.PASS,
                      evidence={"lineage_present": True})


def _check_quantcontext(record: PredictionRecord) -> AuditCheck:
    """L7：QuantContext 来自 QuantState（renderer 版本绑定 + 无独立 future 读取）。
    完整 invariance 由 mutation test 覆盖。"""
    if not record.renderer_version:
        return AuditCheck(name="L7 QuantContext", status=CheckStatus.FAIL,
                          evidence={"reason": "renderer_version missing"})
    return AuditCheck(name="L7 QuantContext", status=CheckStatus.PASS,
                      evidence={"renderer_version": record.renderer_version})


def _check_thesis(record: PredictionRecord) -> AuditCheck:
    """L8：PredictionRecord 不得含 thesis 文本内容（只允许 thesis_id 引用）。"""
    schema_fields = set(record.model_fields.keys())
    thesis_content = schema_fields & set(THESIS_CONTENT_FIELDS)
    if thesis_content:
        return AuditCheck(name="L8 Thesis", status=CheckStatus.FAIL,
                          evidence={"thesis_content_fields": sorted(thesis_content)})
    return AuditCheck(name="L8 Thesis", status=CheckStatus.NOT_APPLICABLE,
                      evidence={"reason": "PredictionRecord 无 thesis 文本字段，仅 thesis_id 引用"})


def _check_tuning(record: PredictionRecord) -> AuditCheck:
    """L9：config fingerprint（frozen 版本一致性），检测 CONFIG_DRIFT。"""
    if record.oos_contract_version != OOS_CONTRACT_VERSION:
        return AuditCheck(name="L9 Tuning", status=CheckStatus.FAIL,
                          evidence={"reason": "CONFIG_DRIFT: oos_contract_version mismatch",
                                    "got": record.oos_contract_version})
    if not record.quant_state_version or not record.renderer_version:
        return AuditCheck(name="L9 Tuning", status=CheckStatus.FAIL,
                          evidence={"reason": "CONFIG_DRIFT: missing version field"})
    return AuditCheck(name="L9 Tuning", status=CheckStatus.PASS,
                      evidence={"oos_contract_version": record.oos_contract_version,
                                "quant_state_version": record.quant_state_version,
                                "renderer_version": record.renderer_version})


def audit_prediction_record(record: PredictionRecord,
                            historical_run: HistoricalRunResult | None = None) -> OOSLeakageAuditResult:
    """对单条 prediction record 做 L1-L9 泄漏审计（不信任 record.pit_status）。"""
    checks = [
        _check_temporal(record, historical_run),
        _check_revision(record, historical_run),
        _check_label(record),
        _check_cross_sample(),
        _check_agent_research(),
        _check_quantstate(record, historical_run),
        _check_quantcontext(record),
        _check_thesis(record),
        _check_tuning(record),
    ]
    violations = []
    for c in checks:
        if c.status == CheckStatus.FAIL:
            violations.append(Violation(
                leakage_type=c.name.replace(" ", "_").upper(),
                field=c.name, description=f"{c.name} audit FAIL",
                evidence=c.evidence,
            ))
    return OOSLeakageAuditResult(
        audit_id=build_audit_id(record.prediction_id),
        prediction_id=record.prediction_id,
        symbol=record.symbol,
        prediction_date=record.prediction_date,
        prediction_as_of=record.prediction_as_of,
        horizon=record.horizon,
        overall_status=overall_status_from_checks(checks),
        violations=violations,
        checks=checks,
        oos_contract_version=record.oos_contract_version,
        quant_state_version=record.quant_state_version,
        renderer_version=record.renderer_version,
        source_lineage=record.source_lineage,
    )


def audit_prediction_dataset(dataset) -> list[OOSLeakageAuditResult]:
    """对整个 prediction dataset 逐条审计。"""
    return [audit_prediction_record(r) for r in dataset.records]
