# -*- coding: utf-8 -*-
"""Availability Contract 基础测试（P7 STEP 6.5B）。"""
from datetime import timezone

from quant_engine.oos.availability_models import (
    AvailabilityEvidence, AvailabilityStatus, utc_iso,
)
from quant_engine.oos.availability_audit import audit_availability, audit_evidence_list


def test_evidence_frozen():
    e = AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN,
        available_at=utc_iso("2024-05-30"),
        source="sec_edgar", source_field="filed",
        record_id="r1", as_of=utc_iso("2024-06-03"),
        reason="filed <= T",
    )
    try:
        e.status = AvailabilityStatus.VIOLATION  # type: ignore[misc]
        assert False, "frozen model 应禁止修改"
    except Exception:
        pass


def test_deterministic_serialization():
    e1 = AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN, available_at=utc_iso("2024-05-30"),
        source="sec_edgar", source_field="filed", record_id="r1",
        as_of=utc_iso("2024-06-03"), reason="x",
    )
    e2 = AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN, available_at=utc_iso("2024-05-30"),
        source="sec_edgar", source_field="filed", record_id="r1",
        as_of=utc_iso("2024-06-03"), reason="x",
    )
    assert e1.model_dump_json() == e2.model_dump_json()
    assert e1.model_dump()["available_at"].tzinfo == timezone.utc


def test_audit_proven_safe():
    e = AvailabilityEvidence(status=AvailabilityStatus.PROVEN,
                             available_at=utc_iso("2024-05-30"), source="s",
                             source_field="f", record_id="r", as_of=utc_iso("2024-06-03"), reason="x")
    assert audit_availability(e) == "SAFE"


def test_audit_unverifiable_blocked():
    e = AvailabilityEvidence(status=AvailabilityStatus.UNVERIFIABLE,
                             available_at=None, source="s", source_field=None,
                             record_id="r", as_of=utc_iso("2024-06-03"), reason="x")
    assert audit_availability(e) == "BLOCKED"


def test_audit_violation_unsafe():
    e = AvailabilityEvidence(status=AvailabilityStatus.VIOLATION,
                             available_at=utc_iso("2024-06-10"), source="s",
                             source_field="f", record_id="r", as_of=utc_iso("2024-06-03"), reason="x")
    assert audit_availability(e) == "UNSAFE"


def test_aggregation_fail_closed():
    safe = AvailabilityEvidence(status=AvailabilityStatus.PROVEN,
                                available_at=utc_iso("2024-05-30"), source="s",
                                source_field="f", record_id="safe", as_of=utc_iso("2024-06-03"), reason="x")
    unv = AvailabilityEvidence(status=AvailabilityStatus.UNVERIFIABLE,
                               available_at=None, source="s", source_field=None,
                               record_id="unv", as_of=utc_iso("2024-06-03"), reason="x")
    # 全 SAFE → SAFE
    assert audit_evidence_list([safe, safe]) == "SAFE"
    # 一个 UNVERIFIABLE → BLOCKED（fail-closed，不因多数 SAFE 而 PASS）
    assert audit_evidence_list([safe, unv]) == "BLOCKED"
