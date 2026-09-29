# -*- coding: utf-8 -*-
"""Quant Data Adapter：按 as_of 返回「当时可见」的数据视图（宽表）。

复用 TradingAgents dataflows/date_window.py 的 PIT 纪律（as_of clamp），
不重造第二套 PIT——同一 SPY 只有一个价格源头。
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from .pit import load_pit


def as_of_view(pit: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    """返回 as_of 时点可见的数据宽表（index=trade_date, columns=field）。"""
    # PIT 铁律：只用 available_at <= as_of 的记录
    visible = pit[pit["available_at"] <= pd.Timestamp(as_of)]
    # 长表 → 宽表，index=交易日，columns=字段
    wide = visible.pivot_table(index="trade_date", columns="field", values="value")
    return wide.sort_index()


def load(as_of: datetime | str, path: str | None = None) -> pd.DataFrame:
    """便捷入口：load(as_of) 返回 as_of 时点可见的宽表。"""
    pit = load_pit(path) if path else load_pit()
    return as_of_view(pit, pd.Timestamp(as_of))


if __name__ == "__main__":
    # 演示：站在 2024-06-03 收盘后，能看到什么、看不到什么
    as_of = pd.Timestamp("2024-06-03 23:59:59")
    wide = load(as_of)
    print(f"as_of={as_of} 时点可见数据到:", wide.index.max().date())
    print("可见行数:", len(wide))
    print(wide.tail(3).round(2).to_string())
