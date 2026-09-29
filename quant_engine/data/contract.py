# -*- coding: utf-8 -*-
"""PIT 数据契约（DATA_CONTRACT.md §1 落地）。

四时间字段语义（日线市场数据，第一版）：
- observation_time：数据反映的时点 = 该交易日收盘
- published_at     ：发布时点     = 该交易日收盘
- available_at     ：真正可用     = 该交易日收盘后（23:59:59 UTC）
- revision_time    ：修订时点（日线不复权修订，恒 None；宏观数据有修正时才填）

回测铁律：as_of=D 时，只有 available_at <= D 且
(revision_time is None or revision_time > D) 的记录可见。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DataPoint(BaseModel):
    symbol: str
    field: str
    value: float
    observation_time: datetime
    published_at: datetime
    available_at: datetime
    revision_time: datetime | None = None
    pit_quality: str = "ok"      # "ok" | "unknown"
    missing_reason: str | None = None

    def visible_at(self, as_of: datetime) -> bool:
        """as_of 时点该数据是否可见（PIT 铁律）。"""
        if self.available_at > as_of:
            return False
        # 已被修订（revision_time <= as_of）说明 as_of 时应看旧快照；
        # 本行代表"新值"，旧快照由 revision 快照层管理，故此处判不可见。
        if self.revision_time is not None and self.revision_time <= as_of:
            return False
        return True
