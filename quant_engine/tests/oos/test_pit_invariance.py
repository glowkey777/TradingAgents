# -*- coding: utf-8 -*-
"""PIT invariance 测试（P7 STEP 6.2，critical）。

future mutation invariance：修改 T 之后数据，QuantState(T) 不变。
revision mutation invariance：修改 revision_time > as_of 的数据，QuantState(T) 不变。
determinism：相同输入两次运行，system-owned fields 一致。
"""
from datetime import date, datetime

import pandas as pd
import pytest

from quant_engine.oos.pit_runner import run_historical_t
from quant_engine.oos.run_models import RunStatus


def _patched_load_wide(fb, mutate_future: bool):
    """构造一个 load_wide：先加载完整数据，可选把 T+1 之后的 close 改成极端值，再 as_of 过滤。"""
    orig = fb.load_wide

    def modified(frequency, as_of=None):
        frames = [pd.read_parquet(f) for f in sorted((fb.INGEST / frequency).glob("*.parquet"))]
        df = pd.concat(frames, ignore_index=True)
        if mutate_future and "close" in set(df["field"]):
            mask = (df["field"] == "close") & \
                   (pd.to_datetime(df["available_at"]) > pd.Timestamp("2024-06-03 23:59:59"))
            df.loc[mask, "value"] = 99999.0
        if as_of is not None:
            avail = pd.to_datetime(df["available_at"])
            df = df[avail <= pd.Timestamp(as_of)]
        wide = df.pivot_table(index="timestamp", columns="field", values="value", aggfunc="last")
        wide.index = pd.to_datetime(wide.index)
        return wide.sort_index()

    return modified


def test_future_mutation_invariance(monkeypatch):
    import quant_engine.features.base as fb

    # 1. baseline（原始数据）
    r1 = run_historical_t("SPY", date(2024, 6, 3))
    assert r1.status == RunStatus.PASS
    baseline_market = r1.quant_state["market"]

    # 2. monkeypatch：T+1 之后的 close 改成极端值
    monkeypatch.setattr(fb, "load_wide", _patched_load_wide(fb, mutate_future=True))

    # 3. 重新运行 → QuantState(T) 的 market 必须不变
    r2 = run_historical_t("SPY", date(2024, 6, 3))
    assert r2.status == RunStatus.PASS
    assert r2.quant_state["market"] == baseline_market
    # 关键：close 仍是 T 的 close，不是被改的 99999
    assert r2.quant_state["market"]["close"] != 99999.0


def test_revision_mutation_invariance(monkeypatch):
    import quant_engine.features.base as fb

    r1 = run_historical_t("SPY", date(2024, 6, 3))
    baseline_market = r1.quant_state["market"]

    # 未来修订（revision_time > as_of）修改 T 的 close 为极端值 → 应被拒绝，QuantState 不变
    def modified(frequency, as_of=None):
        frames = [pd.read_parquet(f) for f in sorted((fb.INGEST / frequency).glob("*.parquet"))]
        df = pd.concat(frames, ignore_index=True)
        if "revision_time" in df.columns and "close" in set(df["field"]):
            mask = (df["field"] == "close") & \
                   (pd.to_datetime(df.get("revision_time")) > pd.Timestamp("2024-06-03 23:59:59"))
            df.loc[mask, "value"] = 99999.0
        if as_of is not None:
            avail = pd.to_datetime(df["available_at"])
            df = df[avail <= pd.Timestamp(as_of)]
        wide = df.pivot_table(index="timestamp", columns="field", values="value", aggfunc="last")
        wide.index = pd.to_datetime(wide.index)
        return wide.sort_index()

    monkeypatch.setattr(fb, "load_wide", modified)
    r2 = run_historical_t("SPY", date(2024, 6, 3))
    assert r2.quant_state["market"] == baseline_market


def test_determinism():
    r1 = run_historical_t("SPY", date(2024, 6, 3))
    r2 = run_historical_t("SPY", date(2024, 6, 3))
    # system-owned artifacts 必须完全一致
    assert r1.quant_state == r2.quant_state
    assert r1.quant_context == r2.quant_context
    assert r1.p4_regime == r2.p4_regime
    assert r1.p5_probability == r2.p5_probability
    assert r1.source_lineage == r2.source_lineage
    assert r1.quant_state_version == r2.quant_state_version
    assert r1.run_id == r2.run_id


def test_created_at_not_wallclock():
    # created_at 必须来自 as_of semantics，非 wall-clock
    r = run_historical_t("SPY", date(2024, 6, 3))
    # quant_state 的 as_of 是 2024-06-03（不是现在）
    assert r.quant_state["as_of"].startswith("2024-06-03")
