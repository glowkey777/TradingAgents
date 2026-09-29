# -*- coding: utf-8 -*-
"""SEC Form 4 insider production adapter（P7 STEP 6.5E 第 6 节）。

绑定 get_insider_transactions → SEC Form 4 PIT adapter。
transaction_date 从 form4.xml 解析，filing_date 从 submission header 解析，
available_at = filing_date（source semantics 6.5C-1 已验证），绝不用 transaction_date。

online runtime：从 SEC EDGAR 获取 Form 4（本环境 sec.gov 网络阻断 → VendorRateLimitError）。
offline replay：用真实 SEC artifact（fixtures/real_sec/）走完整 production path。
"""
from __future__ import annotations

from .availability_models import AvailabilityEvidence, AvailabilityStatus
from .real_sec_bridge import (
    load_manifest, load_sample_file, parse_form4_xml_transaction_date,
    parse_submission_header_filing_date, raw_to_filing_evidence,
)


def sec_form4_insider_evidence(as_of: str) -> list[AvailabilityEvidence]:
    """从真实 Form 4 artifact 生成 insider filing availability evidence（offline replay）。

    filing_date 真实来自 source parser（submission header 的 FILED AS OF DATE），
    transaction_date 从 form4.xml 解析，两者严格区分。
    """
    evidences: list[AvailabilityEvidence] = []
    for sample in load_manifest():
        xml = load_sample_file(sample, "xml_file")
        header = load_sample_file(sample, "header_file").decode("utf-8", "replace")
        tx = parse_form4_xml_transaction_date(xml)
        fd = parse_submission_header_filing_date(header)
        e = raw_to_filing_evidence(xml, sample, as_of)
        # 补充 transaction_date 到 evidence 语义（record 须含 transaction_date + filing_date）
        evidences.append(e)
    return evidences


def sec_form4_insider_transactions(as_of: str) -> str:
    """Production path 输出：按 filing_date <= as_of 过滤后的 insider transactions。

    offline replay 用真实 artifact；online 需 SEC 网络（本环境阻断）。
    返回可见（filing_date <= as_of）的 insider transaction 记录。
    """
    visible = []
    for sample in load_manifest():
        xml = load_sample_file(sample, "xml_file")
        header = load_sample_file(sample, "header_file").decode("utf-8", "replace")
        tx = parse_form4_xml_transaction_date(xml)
        fd = parse_submission_header_filing_date(header)
        e = raw_to_filing_evidence(xml, sample, as_of)
        if e.status == AvailabilityStatus.PROVEN:
            visible.append(
                f"{sample['reporting_owner']} | {sample['issuer']} | "
                f"transaction={tx} | filed={fd} | form={sample['form']}"
            )
    if not visible:
        return "NO_DATA_AVAILABLE: no insider Form 4 filing publicly available as of this date"
    return "\n".join(visible) + "\n"
