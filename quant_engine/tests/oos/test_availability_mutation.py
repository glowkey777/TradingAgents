# -*- coding: utf-8 -*-
"""Availability mutation tests（P7 STEP 6.5B 第 11 节四组 mutation）。"""
from quant_engine.oos.availability_models import AvailabilityStatus
from quant_engine.oos.availability_adapters import (
    sec_edgar_fact_availability, yfinance_statement_availability, insider_availability,
)
from quant_engine.oos.availability_audit import audit_availability


AS_OF = "2024-06-03"


# ── Mutation A：period_end <= T, filing_date > T ──
def test_mutation_a_period_end_canary():
    """period_end <= T 但 filing 在未来：yfinance 无 filing date → UNVERIFIABLE（绝不 PASS）。"""
    e = yfinance_statement_availability("2024-05-31", "r1", AS_OF)
    assert e.status == AvailabilityStatus.UNVERIFIABLE
    assert audit_availability(e) == "BLOCKED"


def test_mutation_a_edgar_filing_future_violation():
    """SEC EDGAR 有 filed：filed > T → VIOLATION（UNSAFE，正确拒绝）。"""
    e = sec_edgar_fact_availability({"filed": "2024-06-10", "end": "2024-03-31", "val": 100}, "r1", AS_OF)
    assert e.status == AvailabilityStatus.VIOLATION
    assert audit_availability(e) == "UNSAFE"


# ── Mutation B：period_end <= T, filing_date <= T（legitimate）──
def test_mutation_b_legitimate_filing():
    e = sec_edgar_fact_availability({"filed": "2024-05-30", "end": "2024-03-31", "val": 100}, "r1", AS_OF)
    assert e.status == AvailabilityStatus.PROVEN
    assert audit_availability(e) == "SAFE"


# ── Mutation C：filing_date <= T, revision_time > T ──
def test_mutation_c_future_revision_rejected():
    """原始 fact（filed<=T）保留，修订 fact（filed>T）拒绝 → revision isolation。"""
    original = sec_edgar_fact_availability({"filed": "2024-05-30", "end": "2024-03-31", "val": 100}, "orig", AS_OF)
    revision = sec_edgar_fact_availability({"filed": "2024-06-10", "end": "2024-03-31", "val": 120}, "rev", AS_OF)
    assert original.status == AvailabilityStatus.PROVEN
    assert revision.status == AvailabilityStatus.VIOLATION
    # T 时只能看到 original 值（100），看不到 restatement 值（120）
    assert audit_availability(original) == "SAFE"
    assert audit_availability(revision) == "UNSAFE"


# ── Mutation D：transaction_date <= T, filing_date > T ──
def test_mutation_d_insider_filing_future_violation():
    """有 filing_date 的 vendor：filing_date > T → VIOLATION。"""
    e = insider_availability(transaction_date="2024-06-01", filing_date="2024-06-05",
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.VIOLATION
    assert audit_availability(e) == "UNSAFE"


def test_mutation_d_insider_no_filing_date_unverifiable():
    """当前 vendor 无 Form 4 filing date → UNVERIFIABLE（绝不 PASS）。"""
    e = insider_availability(transaction_date="2024-06-01", filing_date=None,
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.UNVERIFIABLE
    assert audit_availability(e) == "BLOCKED"


def test_mutation_d_insider_legitimate_filing():
    """filing_date <= T → PROVEN（仅当 vendor 提供 filing_date）。"""
    e = insider_availability(transaction_date="2024-06-01", filing_date="2024-05-28",
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.PROVEN
    assert audit_availability(e) == "SAFE"
