# -*- coding: utf-8 -*-
"""Production Mutation 测试（P7 STEP 6.5D 第 8/9/10 节）。

在 production path 上验证 availability 过滤：future filing 拒绝、legitimate 保留、revision 拒绝。
用真实 SEC Form 4 artifact（6.5C-1）+ sec_edgar _as_of 语义。
"""
from quant_engine.oos.availability_models import AvailabilityStatus
from quant_engine.oos.availability_audit import audit_availability
from quant_engine.oos.real_sec_bridge import (
    load_manifest, load_sample_file, parse_form4_xml_transaction_date,
    parse_submission_header_filing_date, raw_to_filing_evidence,
)


def _sample():
    m = load_manifest()
    assert m, "真实样本未登记"
    return m[0]


# ── 第 8 节：future filing canary（transaction<=T 但 filing>T → 不可见）──
def test_production_future_filing_rejected():
    sample = _sample()
    xml = load_sample_file(sample, "xml_file")
    tx = parse_form4_xml_transaction_date(xml)
    fd = parse_submission_header_filing_date(
        load_sample_file(sample, "header_file").decode("utf-8", "replace")
    )
    as_of = "2024-06-26 23:59:59"
    assert tx == "2024-06-26"  # transaction_date <= T
    assert fd == "2024-06-27"  # filing_date > T
    e = raw_to_filing_evidence(xml, sample, as_of)
    assert e.status == AvailabilityStatus.VIOLATION  # 未来 filing → 拒绝


# ── 第 9 节：legitimate control（transaction < filing <= T → 保留）──
def test_production_legitimate_filing_retained():
    sample = _sample()
    xml = load_sample_file(sample, "xml_file")
    as_of = "2024-06-27 23:59:59"  # filing_date=06-27 <= T
    e = raw_to_filing_evidence(xml, sample, as_of)
    assert e.status == AvailabilityStatus.PROVEN
    assert audit_availability(e) == "SAFE"


# ── 第 10 节：revision canary（sec_edgar 无 revision semantics → UNVERIFIABLE，不猜）──
def test_production_revision_no_semantics_unverifiable():
    """sec_edgar 的 filed 是 filing date，无独立 revision_time 字段 → 不假装 revision semantics。"""
    # SEC EDGAR companyfacts 无 revision_time 字段（filed 是 filing date，amendment 靠 filed 覆盖）
    # 因此 revision 语义由 filed vintage 承担（_as_of 取最新 filed），无独立 revision 字段
    from quant_engine.oos.production_availability_matrix import build_production_matrix
    entries = build_production_matrix()
    ins = next(e for e in entries if e.tool_name == "get_insider_transactions")
    # insider 生产无 filing date（yfinance），revision 无法建立 → UNVERIFIABLE
    assert ins.runtime_pit_status == "UNVERIFIABLE"


# ── sec_edgar statement 无 revision_time 字段：revision 由 filed vintage 承担 ──
def test_sec_edgar_revision_via_filed_vintage():
    """未来 amendment（filed > T）被过滤 = revision 拒绝。"""
    from tradingagents.dataflows.vendors.sec_edgar import _as_of
    facts = {
        "Assets": {
            "units": {
                "USD": [
                    {"filed": "2024-05-15", "end": "2024-03-31", "val": 100.0, "form": "10-Q"},
                    # restatement filed 2024-06-10（> T=2024-06-03）→ 未来 revision，不可见
                    {"filed": "2024-06-10", "end": "2024-03-31", "val": 95.0, "form": "10-Q/A"},
                ]
            }
        }
    }
    values, _ = _as_of(facts, ("Assets",), "2024-06-03", (60, 115))
    # 只有 filed<=T 的 100.0 可见，未来 restatement 95.0 被过滤
    assert values["2024-03-31"] == 100.0
