# -*- coding: utf-8 -*-
"""PIT Guard（P7 STEP 6.2）。

runner-level PIT firewall：在数据进入 P1-P6 pipeline 前约束
available_at <= as_of 且 revision_time <= as_of；再对最终 QuantState 做 post-build audit。
不只在最终 QuantState 上检查——pre-ingestion + post-build 双重防线。
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from .run_models import PITAuditRecord


class PITGuard:
    """给定 requested_as_of，对任何 input artifact 做 PIT 约束。"""

    def __init__(self, requested_as_of: datetime):
        self._as_of = pd.Timestamp(requested_as_of)

    @property
    def as_of(self) -> datetime:
        return self._as_of.to_pydatetime()

    def available_at_ok(self, available_at) -> bool:
        """available_at <= as_of → eligible；> as_of → REJECT。"""
        if available_at is None:
            return True
        return pd.Timestamp(available_at) <= self._as_of

    def revision_time_ok(self, revision_time) -> bool:
        """revision_time <= as_of 或缺失 → 允许；> as_of → REJECT（未来修订值）。"""
        if revision_time is None:
            return True
        ts = pd.Timestamp(revision_time)
        if pd.isna(ts):
            return True
        return ts <= self._as_of

    def audit_pit_df(self, pit_df: pd.DataFrame) -> PITAuditRecord:
        """pre-ingestion audit：检查数据源。

        future_rows（available_at > as_of）只是信息——数据源含全历史是正常的，
        不判 VIOLATION；revision_rows（revision_time > as_of）才是未来修订泄漏。
        max_available_at 记录 as_of 可见的最后 available_at（<= as_of）。
        """
        future_rows = 0
        revision_rows = 0
        max_available_at = None
        max_revision_time = None
        max_observation_time = None

        if pit_df is not None and not pit_df.empty:
            avail = pd.to_datetime(pit_df["available_at"], errors="coerce")
            future_rows = int((avail > self._as_of).sum())
            visible = avail[avail <= self._as_of]
            if visible.notna().any():
                max_available_at = visible.max().to_pydatetime()

            if "revision_time" in pit_df.columns:
                rev = pd.to_datetime(pit_df["revision_time"], errors="coerce")
                revision_rows = int((rev > self._as_of).sum())
                rev_valid = rev.dropna()
                if not rev_valid.empty:
                    max_revision_time = rev_valid.max().to_pydatetime()

            if "observation_time" in pit_df.columns:
                obs = pd.to_datetime(pit_df["observation_time"], errors="coerce").dropna()
                if not obs.empty:
                    max_observation_time = obs.max().to_pydatetime()

        status = "VIOLATION" if revision_rows else "PASS"
        return PITAuditRecord(
            pit_check_status=status,
            max_observation_time=max_observation_time,
            max_available_at=max_available_at,
            max_revision_time=max_revision_time,
            prediction_as_of=self._as_of.to_pydatetime(),
            future_rows_detected=future_rows,
            revision_rows_detected=revision_rows,
        )

    def audit_quant_state(self, quant_state) -> PITAuditRecord:
        """post-build audit：QuantState 的 observation/trading_date 不得晚于 as_of。"""
        future = 0
        max_obs = None
        if quant_state is not None:
            m = getattr(quant_state, "market", None)
            td = getattr(m, "trading_date", None)
            if td is not None and pd.Timestamp(td) > self._as_of:
                future += 1
            max_obs = getattr(quant_state, "as_of", None)
        status = "VIOLATION" if future else "PASS"
        return PITAuditRecord(
            pit_check_status=status,
            max_observation_time=max_obs,
            max_available_at=None,
            max_revision_time=None,
            prediction_as_of=self._as_of.to_pydatetime(),
            future_rows_detected=future,
            revision_rows_detected=0,
        )
