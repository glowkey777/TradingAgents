# -*- coding: utf-8 -*-
"""Production SEC Router 测试（P7 STEP 6.5E 第 4/6 节）。

验证 SEC fundamentals path（filed PIT）+ SEC insider path（filing_date PIT）。
"""
from quant_engine.oos.availability_models import AvailabilityStatus
from quant_engine.oos.availability_audit import audit_availability
from quant_engine.oos.real_sec_bridge import (
    load_manifest, load_sample_file, parse_form4_xml_transaction_date,
    parse_submission_header_filing_date, raw_to_filing_evidence,
)


# ── SEC fundamentals path：filed PIT ──
def test_sec_fundamentals_filed_pit():
    """sec_edgar _as_of：filed <= curr_date 保留，filed > curr_date 过滤。"""
    from tradingagents.dataflows.vendors.sec_edgar import _as_of
    facts = {
        "Revenue": {
            "units": {
                "USD": [
                    {"filed": "2024-05-15", "start": "2024-01-01", "end": "2024-03-31", "val": 1000.0, "form": "10-Q"},
                    {"filed": "2024-06-10", "start": "2024-01-01", "end": "2024-03-31", "val": 999.0, "form": "10-Q/A"},
                ]
            }
        }
    }
    values, _ = _as_of(facts, ("Revenue",), "2024-06-03", (60, 115))
    # 只有 filed=2024-05-15（<=T）的 1000.0；未来 amendment 999.0 被过滤
    assert values["2024-03-31"] == 1000.0


# ── SEC insider path：filing_date PIT ──
def _sample():
    return load_manifest()[0]


def test_sec_insider_filing_date_pit_visible_after_filing():
    sample = _sample()
    xml = load_sample_file(sample, "xml_file")
    e = raw_to_filing_evidence(xml, sample, "2024-06-27 23:59:59")
    assert e.status == AvailabilityStatus.PROVEN
    assert audit_availability(e) == "SAFE"


def test_sec_insider_filing_date_pit_hidden_before_filing():
    sample = _sample()
    xml = load_sample_file(sample, "xml_file")
    e = raw_to_filing_evidence(xml, sample, "2024-06-26 23:59:59")
    assert e.status == AvailabilityStatus.VIOLATION  # filing_date=06-27 > T


def test_sec_insider_transaction_date_not_available_at():
    """transaction_date=06-26 ≠ available_at=06-27（真实 source）。"""
    sample = _sample()
    xml = load_sample_file(sample, "xml_file")
    header = load_sample_file(sample, "header_file").decode("utf-8", "replace")
    tx = parse_form4_xml_transaction_date(xml)
    fd = parse_submission_header_filing_date(header)
    assert tx == "2024-06-26"
    assert fd == "2024-06-27"
    assert tx != fd  # transaction_date 绝不等于 filing_date/available_at
