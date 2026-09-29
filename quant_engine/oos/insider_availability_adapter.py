# -*- coding: utf-8 -*-
"""InsiderAvailabilityAdapter（P7 STEP 6.5C 第 7 节）。

复用 STEP 6.5B 的 HistoricalAvailabilityProvider Protocol + AvailabilityEvidence，
不重新发明第二套 availability contract。

SEC EDGAR submissions 的 Form 4 filing metadata → AvailabilityEvidence：
filingDate（Form 4 提交日 = 公开可获得时间）<= T → PROVEN。
"""
from __future__ import annotations

from .availability_models import AvailabilityEvidence, AvailabilityStatus, utc_iso


def sec_edgar_insider_filing_availability(filing: dict, as_of: str) -> AvailabilityEvidence:
    """SEC EDGAR submissions 的单个 Form 4 filing → AvailabilityEvidence。

    filing（SEC_EDGAR_SUBMISSIONS_V1 columnar entry，同索引对齐）：
        form: "4" / "4/A"（amendment）
        filingDate: Form 4 提交到 SEC 的日期（YYYY-MM-DD）
        accessionNumber: 唯一 filing 标识
        acceptanceDateTime: 精确到秒的 acceptance 时间

    fail-closed（用户第 8 节）：
        filingDate None  → UNVERIFIABLE
        filingDate > T   → VIOLATION
        否则             → PROVEN（available_at = filingDate）

    amendment（4/A）按自己的 filingDate 计：原始 4 在 T 前 filed 可见，
    修订 4/A 在 T 后 filed 则不可见（revision isolation 由 filingDate 天然保证）。
    transaction_date 不进入 PROVEN 判断。
    """
    form = filing.get("form")
    filing_date = filing.get("filingDate")
    accession = filing.get("accessionNumber")
    record_id = accession or "unknown"

    if filing_date is None:
        return AvailabilityEvidence(
            status=AvailabilityStatus.UNVERIFIABLE,
            available_at=None, source="sec_edgar", source_field=None,
            record_id=record_id, as_of=utc_iso(as_of),
            reason="Form 4 filing 无 filingDate 字段，available_at 无法建立",
        )

    if utc_iso(filing_date) > utc_iso(as_of):
        return AvailabilityEvidence(
            status=AvailabilityStatus.VIOLATION,
            available_at=utc_iso(filing_date),
            source="sec_edgar", source_field="filingDate",
            record_id=record_id, as_of=utc_iso(as_of),
            reason=f"Form 4 filingDate={filing_date} > T（未来 filing，不可见）",
        )

    return AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN,
        available_at=utc_iso(filing_date),
        source="sec_edgar", source_field="filingDate",
        record_id=record_id, as_of=utc_iso(as_of),
        reason=f"Form 4（{form}）filingDate={filing_date} <= T（提交即公开，available_at 已证明）",
    )


def sec_edgar_insider_form4_rows(filings_recent: dict) -> list[dict]:
    """从 submissions API 的 filings.recent（columnar arrays）提取 Form 4 filings。

    filings.recent 是 columnar array（同索引对齐），Form 4 = form in ("4", "4/A")。
    返回 [{form, filingDate, accessionNumber, acceptanceDateTime}, ...]。
    """
    forms = filings_recent.get("form", [])
    filing_dates = filings_recent.get("filingDate", [])
    accessions = filings_recent.get("accessionNumber", [])
    acceptance = filings_recent.get("acceptanceDateTime", [])
    n = min(len(forms), len(filing_dates), len(accessions))
    rows = []
    for i in range(n):
        if forms[i] in ("4", "4/A"):
            rows.append({
                "form": forms[i],
                "filingDate": filing_dates[i],
                "accessionNumber": accessions[i],
                "acceptanceDateTime": acceptance[i] if i < len(acceptance) else None,
            })
    return rows
