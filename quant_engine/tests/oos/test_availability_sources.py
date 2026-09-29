# -*- coding: utf-8 -*-
"""Source Capability 测试（P7 STEP 6.5B 第 12 节 1-6）。"""
from quant_engine.oos.availability_models import AvailabilityStatus, SourceStatus
from quant_engine.oos.availability_source_matrix import build_source_matrix
from quant_engine.oos.availability_adapters import (
    sec_edgar_fact_availability, yfinance_statement_availability,
    alpha_vantage_statement_availability, insider_availability,
)
from quant_engine.oos.availability_audit import audit_availability


AS_OF = "2024-06-03"


def test_yfinance_no_filing_date_unverifiable():
    e = yfinance_statement_availability("2024-05-31", "r1", AS_OF)
    assert e.status == AvailabilityStatus.UNVERIFIABLE
    assert audit_availability(e) == "BLOCKED"


def test_alpha_vantage_no_filing_date_unverifiable():
    e = alpha_vantage_statement_availability("2024-05-31", "r1", AS_OF)
    assert e.status == AvailabilityStatus.UNVERIFIABLE
    assert audit_availability(e) == "BLOCKED"


def test_sec_edgar_filed_proven():
    """SEC EDGAR fact 带 filed <= T → PROVEN（semantics 充分）。"""
    fact = {"filed": "2024-05-30", "end": "2024-03-31", "form": "10-Q", "val": 100}
    e = sec_edgar_fact_availability(fact, "r1", AS_OF)
    assert e.status == AvailabilityStatus.PROVEN
    assert e.available_at.isoformat() == "2024-05-30T00:00:00+00:00"
    assert audit_availability(e) == "SAFE"


def test_sec_edgar_filed_future_violation():
    fact = {"filed": "2024-06-10", "end": "2024-03-31", "form": "10-Q", "val": 100}
    e = sec_edgar_fact_availability(fact, "r1", AS_OF)
    assert e.status == AvailabilityStatus.VIOLATION
    assert audit_availability(e) == "UNSAFE"


def test_sec_edgar_no_filed_unverifiable():
    fact = {"end": "2024-03-31", "val": 100}  # 缺 filed
    e = sec_edgar_fact_availability(fact, "r1", AS_OF)
    assert e.status == AvailabilityStatus.UNVERIFIABLE


def test_insider_no_form4_unverifiable():
    e = insider_availability(transaction_date="2024-06-01", filing_date=None,
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.UNVERIFIABLE
    assert audit_availability(e) == "BLOCKED"


def test_period_end_cannot_substitute_available_at():
    """period_end 不能替代 available_at（用户第 5 节硬规则）。"""
    # period_end <= T 但无 filing date → UNVERIFIABLE（不是 PROVEN）
    e = yfinance_statement_availability("2024-05-31", "r1", AS_OF)
    assert e.status != AvailabilityStatus.PROVEN
    assert e.available_at is None


def test_transaction_date_cannot_substitute_filing_date():
    """transaction_date 不能替代 filing_date（用户第 7 节硬规则）。"""
    e = insider_availability(transaction_date="2024-06-01", filing_date=None,
                             record_id="r1", as_of=AS_OF)
    assert e.status != AvailabilityStatus.PROVEN


def test_source_matrix_statuses():
    m = build_source_matrix()
    # SEC EDGAR 三个 statement 都是 PIT_SAFE
    edgar = [c for c in m if c.vendor == "sec_edgar"]
    assert len(edgar) == 3
    assert all(c.status == SourceStatus.PIT_SAFE for c in edgar)
    assert all(c.filing_field == "filed" for c in edgar)
    # insider 两个 vendor 都 UNVERIFIABLE
    insider = [c for c in m if c.tool == "get_insider_transactions"]
    assert len(insider) == 2
    assert all(c.status == SourceStatus.UNVERIFIABLE for c in insider)
    assert all(c.filing_field is None for c in insider)
    # yfinance / alpha_vantage statement UNVERIFIABLE
    yf_stmt = [c for c in m if c.vendor == "yfinance" and c.tool.startswith("get_")]
    stmt_unv = [c for c in yf_stmt if c.status == SourceStatus.UNVERIFIABLE]
    assert len(stmt_unv) >= 3
