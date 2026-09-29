# -*- coding: utf-8 -*-
"""Historical Availability Provider 的 source adapters（P7 STEP 6.5B 第 4/6 节）。

每个 adapter 把一个 vendor/source 的 record 转成 AvailabilityEvidence。
period_end 与 available_at 语义严格独立。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .availability_models import (
    AvailabilityEvidence, AvailabilityStatus, utc_iso,
)


@runtime_checkable
class HistoricalAvailabilityProvider(Protocol):
    def availability_at(self, record: dict, as_of: str) -> AvailabilityEvidence: ...


def _proven(available_at: str, source: str, field: str, record_id: str, as_of: str) -> AvailabilityEvidence:
    return AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN,
        available_at=utc_iso(available_at),
        source=source, source_field=field, record_id=record_id, as_of=utc_iso(as_of),
        reason=f"{field} = {available_at} <= T（公开可用已证明）",
    )


def _unverifiable(source: str, record_id: str, as_of: str, reason: str) -> AvailabilityEvidence:
    return AvailabilityEvidence(
        status=AvailabilityStatus.UNVERIFIABLE,
        available_at=None, source=source, source_field=None,
        record_id=record_id, as_of=utc_iso(as_of), reason=reason,
    )


def _violation(available_at: str, source: str, field: str, record_id: str, as_of: str) -> AvailabilityEvidence:
    return AvailabilityEvidence(
        status=AvailabilityStatus.VIOLATION,
        available_at=utc_iso(available_at),
        source=source, source_field=field, record_id=record_id, as_of=utc_iso(as_of),
        reason=f"{field} = {available_at} > T（未来公开，不能进入 T 的 observation）",
    )


# ── SEC EDGAR companyfacts（SEC_EDGAR_COMPANYFACTS_V1）──
def sec_edgar_fact_availability(fact: dict, record_id: str, as_of: str) -> AvailabilityEvidence:
    """SEC EDGAR companyfacts 的单个 fact → AvailabilityEvidence。

    SEC_EDGAR_COMPANYFACTS_V1 字段语义：
    - filed：filing date（XBRL 提交到 SEC 的日期，提交即公开）
    - form：10-K / 10-Q / 8-K ...
    - end / start：reporting period
    - val：value
    filed 是真实 available_at（提交日），filed <= T → PROVEN。
    """
    filed = fact.get("filed")
    if filed is None:
        return _unverifiable("sec_edgar", record_id, as_of,
                            "fact 无 filed 字段，available_at 无法建立")
    if utc_iso(filed) <= utc_iso(as_of):
        return _proven(filed, "sec_edgar", "filed", record_id, as_of)
    return _violation(filed, "sec_edgar", "filed", record_id, as_of)


# ── yfinance statement（period_end only）──
def yfinance_statement_availability(period_end: str | None, record_id: str, as_of: str) -> AvailabilityEvidence:
    """yfinance statement：只有 fiscal period end，无 filing date → UNVERIFIABLE。

    period_end 描述"数据代表哪个经济期间"，不是"T 时是否公开可见"。
    """
    return _unverifiable("yfinance", record_id, as_of,
                         f"只有 period_end={period_end}，无 filing date；"
                         "period_end <= T ≠ available_at <= T")


# ── alpha_vantage statement（fiscalDateEnding only）──
def alpha_vantage_statement_availability(fiscal_date_ending: str | None, record_id: str, as_of: str) -> AvailabilityEvidence:
    return _unverifiable("alpha_vantage", record_id, as_of,
                         f"只有 fiscalDateEnding={fiscal_date_ending}，无 filing date；"
                         "fiscalDateEnding <= T ≠ available_at <= T")


# ── insider transactions（transaction_date vs filing_date）──
def insider_availability(
    transaction_date: str | None,
    filing_date: str | None,
    record_id: str,
    as_of: str,
    source: str = "insider_vendor",
) -> AvailabilityEvidence:
    """insider：严格区分 transaction_date 与 Form 4 filing_date。

    - 无 filing_date → UNVERIFIABLE（即使 transaction_date <= T）
    - filing_date <= T → PROVEN
    - filing_date > T → VIOLATION
    """
    if filing_date is None:
        return _unverifiable(source, record_id, as_of,
                             f"只有 transaction_date={transaction_date}，无 Form 4 filing date；"
                             "transaction_date <= T ≠ filing_date <= T")
    if utc_iso(filing_date) <= utc_iso(as_of):
        return _proven(filing_date, source, "filing_date", record_id, as_of)
    return _violation(filing_date, source, "filing_date", record_id, as_of)
