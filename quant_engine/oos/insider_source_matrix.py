# -*- coding: utf-8 -*-
"""Insider Source Capability Matrix（P7 STEP 6.5C 第 4 节）。

记录每个 insider source 的 Form 4 filing/availability capability。只陈述证据，不猜测。
status 只能是 PIT_SAFE / UNVERIFIABLE / UNSAFE / NOT_SUPPORTED。
"""
from __future__ import annotations

from .availability_models import SourceCapability, SourceStatus


def build_insider_source_matrix() -> list[SourceCapability]:
    return [
        # ── 现有 insider vendor（都无 Form 4 filing date）──
        SourceCapability(
            source="Yahoo Finance insider_transactions", vendor="yfinance",
            tool="get_insider_transactions", dataset="Ticker.insider_transactions",
            period_field=None, publication_field=None, filing_field=None,
            availability_field=None, revision_field=None,
            historical_support=False,
            pit_guarantee="无：只按 Start Date（transaction date）切，无 Form 4 filing date",
            coverage="US", limitations="transaction_date ≠ filing_date",
            status=SourceStatus.UNVERIFIABLE,
        ),
        SourceCapability(
            source="Alpha Vantage INSIDER_TRANSACTIONS", vendor="alpha_vantage",
            tool="get_insider_transactions", dataset="INSIDER_TRANSACTIONS",
            period_field=None, publication_field=None, filing_field=None,
            availability_field=None, revision_field=None,
            historical_support=False,
            pit_guarantee="无：只按 transaction_date 切，无 Form 4 filing date",
            coverage="US", limitations="transaction_date ≠ filing_date",
            status=SourceStatus.UNVERIFIABLE,
        ),
        # ── 候选：SEC EDGAR submissions API（Form 4 filing metadata）──
        SourceCapability(
            source="SEC EDGAR submissions", vendor="sec_edgar",
            tool="get_insider_transactions（filing metadata）",
            dataset="https://data.sec.gov/submissions/CIK{cik}.json → filings.recent",
            period_field=None,
            publication_field="acceptanceDateTime（精确到秒）",
            filing_field="filingDate（Form 4 提交日）",
            availability_field="filingDate",
            revision_field="form == '4/A'（amendment）",
            historical_support=True,
            pit_guarantee="filings.recent 是 columnar array：form/filingDate/accessionNumber 同索引对齐；"
                          "filingDate = Form 4 提交到 SEC 的日期，提交即公开；"
                          "amendment（4/A）按自己的 filingDate 计",
            coverage="US SEC filers（需 CIK，ticker map 转换）",
            limitations="submissions 只返回 filing metadata（无 transaction 详情），"
                        "transaction 详情需解析 Form 4 XML（accessionNumber → 下载）",
            status=SourceStatus.PIT_SAFE,
        ),
    ]
