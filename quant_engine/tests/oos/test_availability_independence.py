# -*- coding: utf-8 -*-
"""Availability Auditor 独立性测试（P7 STEP 6.5B 第 13 节）。"""
from quant_engine.oos.availability_models import (
    AvailabilityEvidence, AvailabilityStatus, utc_iso,
)
from quant_engine.oos.availability_audit import audit_availability


def test_source_claims_proven_but_available_at_future():
    """source 声称 PROVEN 但 available_at > T → FAIL（不信任 source 声称）。"""
    e = AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN,
        available_at=utc_iso("2024-06-10"),  # 未来
        source="s", source_field="filed", record_id="r",
        as_of=utc_iso("2024-06-03"), reason="x",
    )
    assert audit_availability(e) == "FAIL"


def test_source_claims_unverifiable_but_valid_available_at():
    """source 声称 UNVERIFIABLE 但 evidence 含 valid available_at <= T → audit 识别 SAFE。

    evidence schema 完整时，auditor 优先看 available_at 事实字段，不盲信 status 声称。
    """
    e = AvailabilityEvidence(
        status=AvailabilityStatus.UNVERIFIABLE,  # source 声称 UNVERIFIABLE
        available_at=utc_iso("2024-05-30"),       # 但事实 available_at <= T
        source="s", source_field="filed", record_id="r",
        as_of=utc_iso("2024-06-03"), reason="x",
    )
    assert audit_availability(e) == "SAFE"


def test_auditor_not_relying_on_status_string():
    """auditor 不依赖 status 字符串，而是独立计算 available_at 与 as_of 的关系。"""
    # 两个 evidence 的 status 相反，但 available_at 事实相同 → 审计结果一致
    a = AvailabilityEvidence(status=AvailabilityStatus.PROVEN,
                             available_at=utc_iso("2024-05-30"), source="s",
                             source_field="f", record_id="a",
                             as_of=utc_iso("2024-06-03"), reason="x")
    b = AvailabilityEvidence(status=AvailabilityStatus.UNVERIFIABLE,
                             available_at=utc_iso("2024-05-30"), source="s",
                             source_field="f", record_id="b",
                             as_of=utc_iso("2024-06-03"), reason="x")
    assert audit_availability(a) == audit_availability(b) == "SAFE"


def test_proven_without_available_at_is_blocked():
    """声称 PROVEN 却无 available_at → 矛盾，按 UNVERIFIABLE（BLOCKED）。"""
    e = AvailabilityEvidence(status=AvailabilityStatus.PROVEN,
                             available_at=None, source="s", source_field="filed",
                             record_id="r", as_of=utc_iso("2024-06-03"), reason="x")
    assert audit_availability(e) == "BLOCKED"
