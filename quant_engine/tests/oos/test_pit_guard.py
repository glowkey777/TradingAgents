# -*- coding: utf-8 -*-
"""PIT Guard 单元测试（P7 STEP 6.2）。"""
from datetime import datetime, timedelta

import pandas as pd

from quant_engine.oos.pit_guard import PITGuard

AS_OF = datetime(2024, 6, 3, 23, 59, 59)


def _guard():
    return PITGuard(AS_OF)


def test_available_at_boundary():
    g = _guard()
    # == as_of → ALLOW
    assert g.available_at_ok(AS_OF)
    # == as_of + epsilon → REJECT
    assert not g.available_at_ok(AS_OF + timedelta(seconds=1))
    # None（合成字段）→ 允许
    assert g.available_at_ok(None)


def test_revision_boundary():
    g = _guard()
    assert g.revision_time_ok(None)                      # 无修订 → 允许
    assert not g.revision_time_ok(datetime(2024, 6, 10))  # 未来修订 → 拒绝
    assert g.revision_time_ok(AS_OF)                     # == as_of → 允许


def test_audit_pit_df_future_rows():
    g = _guard()
    df = pd.DataFrame({
        "trade_date": ["2024-06-03", "2024-06-04"],
        "field": ["spy_close", "spy_close"],
        "value": [512.0, 513.0],
        "available_at": [AS_OF, AS_OF + timedelta(days=1)],
        "revision_time": [pd.NaT, pd.NaT],
    })
    audit = g.audit_pit_df(df)
    assert audit.future_rows_detected == 1
    assert audit.pit_check_status == "PASS"          # future 行只是信息（数据源含全历史正常）
    assert audit.max_available_at == AS_OF            # 可见的最后 available_at 仍 <= as_of


def test_audit_pit_df_revision_rows():
    g = _guard()
    df = pd.DataFrame({
        "trade_date": ["2024-06-03"],
        "field": ["spy_close"],
        "value": [512.0],
        "available_at": [AS_OF],
        "revision_time": [datetime(2024, 6, 10)],  # 未来修订
    })
    audit = g.audit_pit_df(df)
    assert audit.revision_rows_detected == 1
    assert audit.pit_check_status == "VIOLATION"


def test_audit_pit_df_all_pass():
    g = _guard()
    df = pd.DataFrame({
        "trade_date": ["2024-06-03"],
        "field": ["spy_close"],
        "value": [512.0],
        "available_at": [AS_OF],
        "revision_time": [pd.NaT],
    })
    audit = g.audit_pit_df(df)
    assert audit.pit_check_status == "PASS"
    assert audit.future_rows_detected == 0
    assert audit.revision_rows_detected == 0
