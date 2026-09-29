# -*- coding: utf-8 -*-
"""SEC Form 4 insider vendor（PIT-aware，P7 STEP 6.5E）。

Rows are dated by Form 4 filing date (when the market learned of the trade),
not transaction date. A trade is public only when its Form 4 is filed, so a
record is served only when filing_date <= curr_date.

Online runtime needs SEC EDGAR (network); offline replay uses the verified
real-source artifact from STEP 6.5C-1.
"""
from __future__ import annotations

import logging

from tradingagents.dataflows.errors import NoMarketDataError, VendorRateLimitError
from tradingagents.dataflows.vendors.sec_edgar import cik_for

logger = logging.getLogger(__name__)


def _form4_filings_by_cik(cik: str) -> list[dict]:
    """Fetch Form 4 filings for a CIK (online). Returns [{transaction_date, filing_date, form, accession}].

    Raises VendorRateLimitError when SEC is unreachable (current environment).
    """
    # Online path: SEC EDGAR submissions API (network-blocked in this environment).
    # The real-source parser (STEP 6.5C-1) covers the filing-date extraction;
    # here the transport is the single online-only dependency.
    from tradingagents.dataflows.vendors.sec_edgar import _fetch_json

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        data = _fetch_json(url)
    except VendorRateLimitError:
        raise
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    out = []
    for i in range(min(len(forms), len(dates))):
        if forms[i] in ("4", "4/A"):
            out.append({
                "form": forms[i],
                "filing_date": dates[i],
                "accession_number": accessions[i] if i < len(accessions) else None,
                # transaction_date lives in the Form 4 XML, fetched separately online;
                # offline replay supplies it from the real artifact.
                "transaction_date": None,
            })
    return out


def get_insider_transactions(ticker: str, curr_date: str | None = None) -> str:
    """Form 4 filings for ``ticker`` as publicly filed on or before ``curr_date``.

    Only records with filing_date <= curr_date are served. A non-US filer (no CIK)
    is a typed failure, not a fallback to another vendor.
    """
    from datetime import datetime

    canonical = ticker.strip().upper()
    curr_date = curr_date or datetime.now().strftime("%Y-%m-%d")

    cik = cik_for(canonical)
    if cik is None:
        raise NoMarketDataError(
            ticker, canonical,
            "not a US SEC filer — no Form 4 filings available via SEC EDGAR",
        )

    try:
        filings = _form4_filings_by_cik(cik)
    except VendorRateLimitError:
        raise

    visible = [f for f in filings if f["filing_date"] <= curr_date]
    if not visible:
        return (
            f"<no Form 4 filing for {canonical} publicly available on or before {curr_date}>"
        )
    lines = [
        "# Insider transactions (Form 4), dated by filing date — the day the market learned of the trade"
    ]
    for f in visible:
        lines.append(
            f"{canonical} | {f['form']} | filed {f['filing_date']} | accession {f['accession_number']}"
        )
    return "\n".join(lines) + "\n"
