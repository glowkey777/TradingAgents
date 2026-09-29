# -*- coding: utf-8 -*-
"""Real SEC Source Replay Test（P7 STEP 6.5C-1）。

真实 SEC Form 4（ORACLE CORP / Screven Edward / accession 0001127602-24-019342）：
transaction_date=2024-06-26（form4.xml），filing_date=2024-06-27（submission header）。
验证 availability evidence 真实来自 source（parser 提取），非 fixture 手填。
"""
import pytest

from quant_engine.oos.availability_models import (
    AvailabilityEvidence, AvailabilityStatus, utc_iso,
)
from quant_engine.oos.availability_audit import audit_availability
from quant_engine.oos.real_sec_bridge import (
    load_manifest, load_sample_file, parse_form4_xml_transaction_date,
    parse_submission_header_filing_date, raw_to_filing_evidence,
    sha256_bytes, verify_manifest_integrity,
)


def _sample():
    manifest = load_manifest()
    assert manifest, "真实样本未登记（MANIFEST.json 应为真实 SEC Form 4）"
    return manifest[0]


def _xml(sample):
    return load_sample_file(sample, "xml_file")


def _header(sample):
    return load_sample_file(sample, "header_file").decode("utf-8", "replace")


# ── provenance 登记 ──
def test_real_sec_provenance():
    sample = _sample()
    assert sample["evidence_type"] == "REAL_SOURCE"
    assert sample["synthetic"] is False
    assert sample["source"] == "SEC_EDGAR"
    assert sample["accession_number"] == "0001127602-24-019342"
    assert sample["form"] == "4"
    assert sample["issuer"] == "ORACLE CORP"
    assert sample["reporting_owner"] == "Screven Edward"


# ── hash verification ──
def test_real_sec_hash():
    sample = _sample()
    assert verify_manifest_integrity() == []
    xml = _xml(sample)
    assert sha256_bytes(xml) == sample["xml_sha256"]
    header = _header(sample)
    assert sha256_bytes(header.encode("utf-8")) == sample["header_sha256"]


# ── transaction_date 从真实 XML 解析 ──
def test_real_sec_transaction_date_from_xml():
    sample = _sample()
    assert parse_form4_xml_transaction_date(_xml(sample)) == "2024-06-26"


# ── filing_date 从真实 submission header 解析 ──
def test_real_sec_filing_date_from_header():
    sample = _sample()
    assert parse_submission_header_filing_date(_header(sample)) == "2024-06-27"


# ── filing_date 真实来自 source，不是 fixture 手填 ──
def test_filing_date_from_source_not_fixture():
    sample = _sample()
    parsed = parse_submission_header_filing_date(_header(sample))
    assert parsed == "2024-06-27"
    assert sample["filing_date_source_field"] == "FILED AS OF DATE"
    assert parsed == sample["filing_date"]


# ── transaction-date trap ──
def test_real_sec_transaction_date_trap():
    """transaction_date=06-26 <= T=06-26，但 filing_date=06-27 > T → 不可见。

    证明 transaction_date != available_at（真实 source evidence）。
    """
    sample = _sample()
    xml = _xml(sample)
    tx = parse_form4_xml_transaction_date(xml)
    fd = parse_submission_header_filing_date(_header(sample))
    as_of = "2024-06-26 23:59:59"
    assert tx == "2024-06-26" and utc_iso(tx) <= utc_iso(as_of)
    assert fd == "2024-06-27" and utc_iso(fd) > utc_iso(as_of)
    e = raw_to_filing_evidence(xml, sample, as_of)
    assert e.status == AvailabilityStatus.VIOLATION
    assert audit_availability(e) == "UNSAFE"


# ── Replay A（as_of = 2024-06-27 23:59:59 → visible）──
def test_real_sec_visible_after_filing():
    sample = _sample()
    e = raw_to_filing_evidence(_xml(sample), sample, "2024-06-27 23:59:59")
    assert e.status == AvailabilityStatus.PROVEN
    assert e.available_at == utc_iso("2024-06-27")
    assert audit_availability(e) == "SAFE"


# ── Replay B（as_of = 2024-06-26 23:59:59 → not visible）──
def test_real_sec_hidden_before_filing():
    sample = _sample()
    e = raw_to_filing_evidence(_xml(sample), sample, "2024-06-26 23:59:59")
    assert e.status == AvailabilityStatus.VIOLATION
    assert audit_availability(e) == "UNSAFE"


# ── Replay C（as_of = 2024-06-28 23:59:59 → visible）──
def test_real_sec_visible_after_filing2():
    sample = _sample()
    e = raw_to_filing_evidence(_xml(sample), sample, "2024-06-28 23:59:59")
    assert e.status == AvailabilityStatus.PROVEN
    assert audit_availability(e) == "SAFE"


# ── Replay D（same raw, different cutoff）──
def test_real_sec_same_raw_different_cutoff():
    sample = _sample()
    xml = _xml(sample)
    hash_before = sha256_bytes(xml)
    e_t1 = raw_to_filing_evidence(xml, sample, "2024-06-26 23:59:59")
    e_t2 = raw_to_filing_evidence(xml, sample, "2024-06-27 23:59:59")
    assert sha256_bytes(xml) == hash_before
    assert e_t1.status == AvailabilityStatus.VIOLATION
    assert e_t2.status == AvailabilityStatus.PROVEN


# ── raw hash immutability ──
def test_real_sec_hash_immutable():
    sample = _sample()
    xml = _xml(sample)
    h1 = sha256_bytes(xml)
    e = raw_to_filing_evidence(xml, sample, "2024-06-03")
    _ = audit_availability(e)
    assert sha256_bytes(_xml(sample)) == h1
    assert h1 == sample["xml_sha256"]


# ── Independence（auditor 看事实，不信任 status）──
def test_real_sec_independence():
    """source 声称 PROVEN 但 available_at 在未来 → auditor 必须 FAIL。"""
    lying = AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN,
        available_at=utc_iso("2024-06-27"),
        source="sec_edgar", source_field="filingDate",
        record_id="x", as_of=utc_iso("2024-06-26"),
        reason="source 声称 PROVEN 但 available_at > as_of",
    )
    assert audit_availability(lying) == "FAIL"
    honest = AvailabilityEvidence(
        status=AvailabilityStatus.VIOLATION,
        available_at=utc_iso("2024-06-27"),
        source="sec_edgar", source_field="filingDate",
        record_id="x", as_of=utc_iso("2024-06-26"),
        reason="诚实标记未来",
    )
    assert audit_availability(honest) == "UNSAFE"
