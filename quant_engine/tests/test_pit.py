# -*- coding: utf-8 -*-
"""P1 验收测试（纯 assert，不依赖 pytest）。

验收标准（ACCEPTANCE_CRITERIA.md P1）：
1. available_at 正确（= 交易日收盘后，无未来数据泄漏）
2. as_of 取数：站在某时点，看不到之后的数据
3. 数据量与 raw 对齐一致
"""
from __future__ import annotations

import pandas as pd

from quant_engine.data.pit import load_pit, FIELDS
from quant_engine.data.adapter import load, as_of_view
from quant_engine.data.contract import DataPoint


def test_pit_shape():
    pit = load_pit()
    n_days = pit["trade_date"].nunique()
    assert n_days == 3452, f"交易日数应为 3452，实际 {n_days}"
    assert pit["field"].nunique() == len(FIELDS), "字段数不对"
    assert (pit["pit_quality"] == "ok").all(), "pit_quality 应全 ok"
    print(f"[PASS] PIT 长表: {len(pit)} 行, {n_days} 交易日, {pit['field'].nunique()} 字段")


def test_available_at_no_future_leak():
    pit = load_pit()
    # available_at 必须 = trade_date 的 23:59:59（收盘后），不能跨到别的交易日
    expected = pd.to_datetime(pit["trade_date"]).dt.normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
    assert (pit["available_at"] == expected).all(), "available_at 与交易日收盘不一致"
    print("[PASS] available_at = 交易日收盘后，无未来泄漏")


def test_as_of_cutoff():
    as_of = pd.Timestamp("2024-06-03 23:59:59")
    wide = load(as_of)
    assert wide.index.max().date() == pd.Timestamp("2024-06-03").date(), \
        f"as_of=2024-06-03 不应看到 6-04 之后数据，实际到 {wide.index.max().date()}"
    # 抽一个已知值：2024-06-03 的 spy_close 应在，2024-06-04 不应在
    assert pd.Timestamp("2024-06-03") in wide.index
    assert pd.Timestamp("2024-06-04") not in wide.index
    print(f"[PASS] as_of={as_of.date()} 截止到 {wide.index.max().date()}，无未来数据")


def test_visible_at_logic():
    from datetime import datetime, timedelta
    as_of = datetime(2024, 6, 3, 23, 59, 59)
    dp_future = DataPoint(symbol="SPY", field="close", value=1.0,
                          observation_time=datetime(2024, 6, 4),
                          published_at=datetime(2024, 6, 4),
                          available_at=datetime(2024, 6, 4, 23, 59, 59))
    dp_past = DataPoint(symbol="SPY", field="close", value=1.0,
                        observation_time=datetime(2024, 6, 3),
                        published_at=datetime(2024, 6, 3),
                        available_at=datetime(2024, 6, 3, 23, 59, 59))
    assert dp_future.visible_at(as_of) is False, "未来数据应不可见"
    assert dp_past.visible_at(as_of) is True, "已收盘数据应可见"
    print("[PASS] DataPoint.visible_at 未来数据不可见、已收盘可见")


if __name__ == "__main__":
    test_pit_shape()
    test_available_at_no_future_leak()
    test_as_of_cutoff()
    test_visible_at_logic()
    print("\n✅ P1 验收全部通过")
