# -*- coding: utf-8 -*-
"""OOS Leakage mutation tests（P7 STEP 6.4）：future / revision / canary。"""
from datetime import date, datetime

import pandas as pd
import pytest

from quant_engine.oos.pit_runner import run_historical_t
from quant_engine.oos.models import Horizon
from quant_engine.oos.dataset_builder import build_prediction_record

CANARY = 999999999.0
T = date(2024, 6, 3)


def _patched_load_wide(fb, mutate: bool):
    def modified(frequency, as_of=None):
        frames = [pd.read_parquet(f) for f in sorted((fb.INGEST / frequency).glob("*.parquet"))]
        df = pd.concat(frames, ignore_index=True)
        if mutate and "close" in set(df["field"]):
            mask = (df["field"] == "close") & \
                   (pd.to_datetime(df["available_at"]) > pd.Timestamp("2024-06-03 23:59:59"))
            df.loc[mask, "value"] = CANARY
        if as_of is not None:
            avail = pd.to_datetime(df["available_at"])
            df = df[avail <= pd.Timestamp(as_of)]
        wide = df.pivot_table(index="timestamp", columns="field", values="value", aggfunc="last")
        wide.index = pd.to_datetime(wide.index)
        return wide.sort_index()
    return modified


def test_future_mutation_invariance(monkeypatch):
    import quant_engine.features.base as fb

    hr1 = run_historical_t("SPY", T)
    rec1 = build_prediction_record(hr1, Horizon.T1)
    market1 = hr1.quant_state["market"]
    p5_1 = hr1.p5_probability

    monkeypatch.setattr(fb, "load_wide", _patched_load_wide(fb, mutate=True))

    hr2 = run_historical_t("SPY", T)
    rec2 = build_prediction_record(hr2, Horizon.T1)
    market2 = hr2.quant_state["market"]
    p5_2 = hr2.p5_probability

    # PredictionRecord / QuantState market / P5 全部不变
    assert rec1 == rec2
    assert market1 == market2
    assert p5_1 == p5_2


def test_canary_not_in_quantstate(monkeypatch):
    import quant_engine.features.base as fb
    monkeypatch.setattr(fb, "load_wide", _patched_load_wide(fb, mutate=True))
    hr = run_historical_t("SPY", T)
    # canary 值绝不得进入 prediction-side artifact
    assert hr.quant_state["market"]["close"] != CANARY
    for field, val in hr.quant_state["market"].items():
        assert val != CANARY, f"{field} 泄漏了 future canary"


def test_canary_not_in_prediction_record(monkeypatch):
    import quant_engine.features.base as fb
    monkeypatch.setattr(fb, "load_wide", _patched_load_wide(fb, mutate=True))
    hr = run_historical_t("SPY", T)
    rec = build_prediction_record(hr, Horizon.T1)
    payload = rec.model_dump(mode="json")
    flat = str(payload)
    assert str(CANARY) not in flat


def test_revision_mutation_audit_fail():
    # 未来 revision（revision_time > as_of）→ audit L2 FAIL（fail-closed）
    from quant_engine.oos.run_models import HistoricalRunResult, RunStatus, PITAuditRecord
    from quant_engine.oos.leakage_models import CheckStatus
    from quant_engine.oos.leakage_audit import audit_prediction_record
    from quant_engine.oos.dataset_models import PredictionRecord

    as_of = datetime(2024, 6, 3, 23, 59, 59)
    hr = HistoricalRunResult(
        run_id="r", symbol="SPY", prediction_date=T, prediction_as_of=as_of,
        horizon="T+1", status=RunStatus.PASS,
        p5_probability={"t1": {"p_up": 0.321, "p_flat": 0.4314, "p_down": 0.2476}},
        quant_state_version="v", renderer_version="v", oos_contract_version="1.0.0",
        source_lineage={"data_version": "p1_canonical_v1"},
        pit_audit=PITAuditRecord(pit_check_status="PASS", prediction_as_of=as_of,
                                 max_revision_time=datetime(2024, 6, 10, 0, 0, 0)),
    )
    rec = build_prediction_record(hr, Horizon.T1)
    result = audit_prediction_record(rec, hr)
    assert result.overall_status == CheckStatus.FAIL
    assert any(v.leakage_type == "L2_REVISION" for v in result.violations)
