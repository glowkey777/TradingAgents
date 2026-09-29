# -*- coding: utf-8 -*-
"""Insider availability 测试（P7 STEP 6.5C 第 9-15 节）。"""
import json
from pathlib import Path

from quant_engine.oos.availability_models import AvailabilityStatus
from quant_engine.oos.availability_adapters import insider_availability
from quant_engine.oos.availability_audit import audit_availability
from quant_engine.oos.insider_availability_adapter import (
    sec_edgar_insider_filing_availability, sec_edgar_insider_form4_rows,
)
from quant_engine.oos.insider_source_matrix import build_insider_source_matrix
from quant_engine.oos.availability_models import SourceStatus

AS_OF = "2024-06-03"
FIXTURE = Path(__file__).parent / "fixtures" / "insider" / "sec_edgar_submissions_aapl.json"


# ── 第 9 节：四个核心测试 ──
def test_1_future_filing_violation():
    """transaction=06-01, filing=06-10（>T）→ VIOLATION，绝不 PROVEN。"""
    e = insider_availability(transaction_date="2024-06-01", filing_date="2024-06-10",
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.VIOLATION
    assert audit_availability(e) == "UNSAFE"


def test_2_legitimate_filing_proven():
    """transaction=06-01, filing=06-02（<=T）→ PROVEN，available_at=06-02。"""
    e = insider_availability(transaction_date="2024-06-01", filing_date="2024-06-02",
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.PROVEN
    assert e.available_at.isoformat() == "2024-06-02T00:00:00+00:00"
    assert audit_availability(e) == "SAFE"


def test_3_transaction_date_cannot_substitute():
    """transaction=06-01, filing=None → UNVERIFIABLE（transaction_date 不能替代）。"""
    e = insider_availability(transaction_date="2024-06-01", filing_date=None,
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.UNVERIFIABLE
    assert audit_availability(e) == "BLOCKED"


def test_4_future_revision_violation():
    """filing=06-02（<=T）但 amendment 4/A filed=06-05（>T）→ 修订 VIOLATION。"""
    original = sec_edgar_insider_filing_availability(
        {"form": "4", "filingDate": "2024-06-02", "accessionNumber": "acc-orig"}, AS_OF)
    amendment = sec_edgar_insider_filing_availability(
        {"form": "4/A", "filingDate": "2024-06-05", "accessionNumber": "acc-amend"}, AS_OF)
    assert original.status == AvailabilityStatus.PROVEN
    assert amendment.status == AvailabilityStatus.VIOLATION


# ── 第 10 节：真实 source replay（fixture-based）──
def test_source_replay_from_fixture():
    """从 fixture 读 SEC submissions 响应，按 filingDate <= T 过滤 Form 4。"""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = sec_edgar_insider_form4_rows(data["filings"]["recent"])
    # 3 个 Form 4 / 4/A（10-K 被排除）
    assert len(rows) == 3
    evidences = [sec_edgar_insider_filing_availability(r, AS_OF) for r in rows]
    statuses = {e.record_id if False else e.status: e for e in evidences}
    # 2024-06-02（<=T）→ PROVEN；2024-06-05、06-10（>T）→ VIOLATION
    by_acc = {e.record_id: e for e in evidences}
    assert by_acc["0000320193-24-000049"].status == AvailabilityStatus.PROVEN
    assert by_acc["0000320193-24-000050"].status == AvailabilityStatus.VIOLATION
    assert by_acc["0000320193-24-000048"].status == AvailabilityStatus.VIOLATION  # 4/A


# ── 第 11 节：current snapshot trap ──
def test_current_snapshot_cannot_prove_historical_availability():
    """当前快照含未来 filing，不能自动证明 T 时可见；必须 record-level filingDate 过滤。"""
    # 当前（2026）快照包含 2024 transaction + 2024 filing
    current_snapshot = [
        {"form": "4", "filingDate": "2024-06-02", "accessionNumber": "acc-old"},
        {"form": "4", "filingDate": "2024-06-10", "accessionNumber": "acc-new"},
    ]
    # 即使快照里有 2024 记录，也必须按 filingDate <= T 筛选
    kept = [f for f in current_snapshot
            if sec_edgar_insider_filing_availability(f, AS_OF).status == AvailabilityStatus.PROVEN]
    assert [f["accessionNumber"] for f in kept] == ["acc-old"]
    # 未过滤的快照不能当作 T 时刻数据集
    assert any(sec_edgar_insider_filing_availability(f, AS_OF).status == AvailabilityStatus.VIOLATION
               for f in current_snapshot)


# ── 第 12 节：cache isolation ──
def test_insider_cache_isolation():
    """as_of=T 的过滤隔离未来 filing（即使 cache 含未来 filing）。"""
    # 模拟 cache 含未来 filing（T+1）
    cached_filings = [
        {"form": "4", "filingDate": "2024-06-02", "accessionNumber": "acc-1"},
        {"form": "4", "filingDate": "2024-06-04", "accessionNumber": "acc-future"},
    ]
    visible_at_T = [f for f in cached_filings
                    if sec_edgar_insider_filing_availability(f, AS_OF).status == AvailabilityStatus.PROVEN]
    assert [f["accessionNumber"] for f in visible_at_T] == ["acc-1"]
    assert "acc-future" not in [f["accessionNumber"] for f in visible_at_T]


# ── 第 14 节：negative control ──
def test_negative_control_transaction_before_filing():
    """transaction < filing <= T → PROVEN（不过度过滤）。"""
    e = insider_availability(transaction_date="2024-05-30", filing_date="2024-06-02",
                             record_id="r1", as_of=AS_OF)
    assert e.status == AvailabilityStatus.PROVEN


# ── 第 15 节：independence ──
def test_source_claims_pit_safe_but_filing_future():
    """source_status=PIT_SAFE 但 filingDate > T → auditor 仍 VIOLATION/FAIL。"""
    e = sec_edgar_insider_filing_availability(
        {"form": "4", "filingDate": "2024-06-04", "accessionNumber": "acc"}, AS_OF)
    assert e.status == AvailabilityStatus.VIOLATION
    assert audit_availability(e) == "UNSAFE"


def test_source_claims_unverifiable_but_valid_filing():
    """source_status=UNVERIFIABLE 但 evidence 含 valid filingDate <= T → auditor 识别 PROVEN。"""
    from quant_engine.oos.availability_models import AvailabilityEvidence, utc_iso
    e = AvailabilityEvidence(
        status=AvailabilityStatus.UNVERIFIABLE,  # source 声称 UNVERIFIABLE
        available_at=utc_iso("2024-06-02"),       # 但事实 available_at <= T
        source="sec_edgar", source_field="filingDate", record_id="acc",
        as_of=utc_iso(AS_OF), reason="x",
    )
    assert audit_availability(e) == "SAFE"


# ── source matrix ──
def test_insider_source_matrix():
    m = build_insider_source_matrix()
    # SEC EDGAR submissions = PIT_SAFE（filingDate 字段）
    edgar = [c for c in m if c.vendor == "sec_edgar"]
    assert len(edgar) == 1
    assert edgar[0].status == SourceStatus.PIT_SAFE
    assert edgar[0].filing_field == "filingDate（Form 4 提交日）"
    # yfinance / alpha_vantage insider = UNVERIFIABLE
    unv = [c for c in m if c.tool == "get_insider_transactions" and c.vendor != "sec_edgar"]
    assert len(unv) == 2
    assert all(c.status == SourceStatus.UNVERIFIABLE for c in unv)
