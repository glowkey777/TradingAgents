# -*- coding: utf-8 -*-
"""Production Offline Replay 测试（P7 STEP 6.5E 第 10/11/12 节）。

offline replay 走完整 production path：configured vendor → router → SEC adapter
→ real Form 4 artifact → AvailabilityEvidence → tool output（不是直接调 adapter）。
"""
from quant_engine.oos.real_sec_bridge import (
    load_manifest, load_sample_file, parse_form4_xml_transaction_date,
    parse_submission_header_filing_date,
)


def _real_filings():
    """从真实 Form 4 artifact 构造 SEC 返回的 filings（online 等价结构）。"""
    sample = load_manifest()[0]
    xml = load_sample_file(sample, "xml_file")
    header = load_sample_file(sample, "header_file").decode("utf-8", "replace")
    tx = parse_form4_xml_transaction_date(xml)
    fd = parse_submission_header_filing_date(header)
    return [{
        "form": sample["form"],
        "filing_date": fd,
        "accession_number": sample["accession_number"],
        "transaction_date": tx,
    }]


def _route_insider(as_of: str):
    """通过 router 走 sec_form4 production path（monkeypatch 网络层注入真实 artifact）。"""
    from tradingagents.dataflows import router as router_mod
    from tradingagents.dataflows.vendors import sec_form4

    orig_cik = sec_form4.cik_for
    orig_fetch = sec_form4._form4_filings_by_cik
    orig_vendor = router_mod.get_vendor
    sec_form4.cik_for = lambda ticker: "0001341439"
    sec_form4._form4_filings_by_cik = lambda cik: _real_filings()
    router_mod.get_vendor = lambda category, method=None: "sec_form4"
    try:
        result = router_mod.route_to_vendor("get_insider_transactions", "ORCL", as_of)
    finally:
        sec_form4.cik_for = orig_cik
        sec_form4._form4_filings_by_cik = orig_fetch
        router_mod.get_vendor = orig_vendor
    return result


def test_offline_replay_absent_before_filing():
    """T=2024-06-26 23:59:59（filing_date=06-27 在未来）→ observation absent。"""
    result = _route_insider("2024-06-26 23:59:59")
    assert "no Form 4 filing" in result or "NO_DATA" in result
    assert "filed 2024-06-27" not in result  # 未来 filing 不可见


def test_offline_replay_present_after_filing():
    """T=2024-06-27 23:59:59（>= filing_date）→ observation present。"""
    result = _route_insider("2024-06-27 23:59:59")
    assert "filed 2024-06-27" in result
    assert "0001127602-24-019342" in result


def test_offline_replay_dates_from_source_not_manual():
    """filing_date 来自真实 artifact（submission header），不是测试手填。"""
    f = _real_filings()
    assert f[0]["filing_date"] == "2024-06-27"
    assert f[0]["transaction_date"] == "2024-06-26"
    # filing_date != transaction_date（真实 source 证明）
    assert f[0]["filing_date"] != f[0]["transaction_date"]
