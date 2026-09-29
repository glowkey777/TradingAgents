# -*- coding: utf-8 -*-
"""Production Runtime Trace 测试（P7 STEP 6.5D 第 7/17 节）。

runtime trace 必须来自 tool arguments + raw returned records + timestamp fields +
availability evidence + as_of，不得由 Agent 自己声称（"I only used historical data"）。
"""
from quant_engine.oos.availability_models import AvailabilityStatus, utc_iso
from quant_engine.oos.availability_audit import audit_availability
from quant_engine.oos.real_sec_bridge import (
    load_manifest, load_sample_file, parse_form4_xml_transaction_date,
    parse_submission_header_filing_date, raw_to_filing_evidence,
)


def _build_runtime_trace(as_of: str) -> dict:
    """从真实 SEC Form 4 artifact 构建完整 runtime trace（非 Agent 声称）。"""
    sample = load_manifest()[0]
    xml = load_sample_file(sample, "xml_file")
    header = load_sample_file(sample, "header_file").decode("utf-8", "replace")

    transaction_date = parse_form4_xml_transaction_date(xml)   # 真实 parser
    filing_date = parse_submission_header_filing_date(header)  # 真实 parser
    evidence = raw_to_filing_evidence(xml, sample, as_of)       # 真实 evidence

    return {
        "agent": "fundamentals_analyst",
        "tool": "get_insider_transactions",
        "vendor": "sec_edgar",
        "record_id": sample["accession_number"],
        "transaction_date": transaction_date,
        "filing_date": filing_date,
        "available_at": evidence.available_at.isoformat() if evidence.available_at else None,
        "as_of": as_of,
        "source": evidence.source,
        "source_field": evidence.source_field,
        "status": evidence.status.value,
    }


def test_runtime_trace_has_all_fields():
    trace = _build_runtime_trace("2024-06-27 23:59:59")
    for key in ("agent", "tool", "vendor", "record_id", "transaction_date",
                "filing_date", "available_at", "as_of", "source"):
        assert key in trace and trace[key] is not None


def test_runtime_trace_available_at_is_filing_not_transaction():
    """available_at = filing_date（2024-06-27），绝不等于 transaction_date（2024-06-26）。"""
    trace = _build_runtime_trace("2024-06-27 23:59:59")
    assert trace["transaction_date"] == "2024-06-26"
    assert trace["filing_date"] == "2024-06-27"
    assert trace["available_at"].startswith("2024-06-27")
    assert trace["available_at"] != trace["transaction_date"]


def test_runtime_trace_visible_after_filing():
    """as_of >= filing_date → PROVEN + SAFE。"""
    trace = _build_runtime_trace("2024-06-27 23:59:59")
    assert trace["status"] == "PROVEN"


def test_runtime_trace_hidden_before_filing():
    """as_of < filing_date → VIOLATION（未来 filing 不可见）。"""
    trace = _build_runtime_trace("2024-06-26 23:59:59")
    assert trace["status"] == "VIOLATION"


def test_runtime_trace_independent_audit():
    """independent auditor 看 available_at 事实，不信任 source 声称。"""
    sample = load_manifest()[0]
    xml = load_sample_file(sample, "xml_file")
    e = raw_to_filing_evidence(xml, sample, "2024-06-27 23:59:59")
    assert audit_availability(e) == "SAFE"
    # 未来 as_of → UNSAFE
    e2 = raw_to_filing_evidence(xml, sample, "2024-06-26 23:59:59")
    assert audit_availability(e2) == "UNSAFE"
