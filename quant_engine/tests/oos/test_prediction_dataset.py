# -*- coding: utf-8 -*-
"""OOS Prediction Dataset 测试（P7 STEP 6.3，25 cases）。"""
import inspect
from datetime import date, datetime

import pandas as pd
import pytest
from pydantic import ValidationError

from quant_engine.oos.pit_runner import run_historical_t
from quant_engine.oos.run_models import HistoricalRunResult, RunStatus, PITAuditRecord
from quant_engine.oos.models import Horizon, DirectionalBias
from quant_engine.oos.dataset_models import (
    PredictionRecord, RecordStatus, FORBIDDEN_OUTCOME_FIELDS,
    build_prediction_id, compute_schema_hash, compute_dataset_hash,
)
from quant_engine.oos.dataset_builder import (
    build_prediction_record, build_prediction_dataset,
    DuplicatePredictionIdError, serialize_dataset,
)

T = date(2024, 6, 3)
AS_OF = datetime(2024, 6, 3, 23, 59, 59)
P5 = {
    "t1": {"p_up": 0.3210, "p_flat": 0.4314, "p_down": 0.2476},
    "t2": {"p_up": 0.3000, "p_flat": 0.4000, "p_down": 0.3000},
}


def _run(status=RunStatus.PASS, p5=P5, pit="PASS", prediction_date=T,
         prediction_as_of=AS_OF, **kw):
    base = dict(
        run_id=f"run-{prediction_date.isoformat()}",
        symbol="SPY", prediction_date=prediction_date, prediction_as_of=prediction_as_of,
        horizon="T+1", status=status, p5_probability=p5,
        quant_state_version="quant-state-v1.0.0", renderer_version="quant_context_v1",
        oos_contract_version="1.0.0",
        source_lineage={"data_version": "p1_canonical_v1"},
        pit_audit=PITAuditRecord(pit_check_status=pit, prediction_as_of=prediction_as_of),
    )
    base.update(kw)
    return HistoricalRunResult(**base)


# ── 1-3. valid record / T+1 / T+2 ──
def test_valid_record():
    rec = build_prediction_record(_run(), Horizon.T1)
    assert rec.record_status == RecordStatus.VALID
    assert rec.p_up == pytest.approx(0.3210)
    assert rec.p_flat == pytest.approx(0.4314)
    assert rec.p_down == pytest.approx(0.2476)


def test_valid_t1():
    rec = build_prediction_record(_run(), Horizon.T1)
    assert rec.horizon == Horizon.T1
    assert rec.p_up == pytest.approx(0.3210)


def test_valid_t2():
    rec = build_prediction_record(_run(), Horizon.T2)
    assert rec.horizon == Horizon.T2
    assert rec.p_up == pytest.approx(0.3000)


# ── 4-6. invalid probability / horizon ──
def test_invalid_probability_sum():
    bad = {"t1": {"p_up": 0.5, "p_flat": 0.5, "p_down": 0.5}, "t2": P5["t2"]}
    with pytest.raises(ValidationError):
        build_prediction_record(_run(p5=bad), Horizon.T1)


def test_negative_probability():
    bad = {"t1": {"p_up": -0.1, "p_flat": 0.6, "p_down": 0.5}, "t2": P5["t2"]}
    with pytest.raises(ValidationError):
        build_prediction_record(_run(p5=bad), Horizon.T1)


def test_invalid_horizon():
    with pytest.raises(ValueError):
        Horizon("T+5")


# ── 7-8. PIT status / violation rejection ──
def test_pit_status_propagation():
    rec = build_prediction_record(_run(pit="VIOLATION"), Horizon.T1)
    assert rec.pit_status == "VIOLATION"


def test_pit_violation_rejection():
    rec = build_prediction_record(_run(status=RunStatus.PIT_VIOLATION), Horizon.T1)
    assert rec.record_status == RecordStatus.PIT_VIOLATION
    assert rec.failure_reason is not None


# ── 9-10. future/label field rejection ──
def test_future_field_rejection():
    rec = build_prediction_record(_run(), Horizon.T1)
    d = rec.model_dump()
    assert "future_close" not in d and "future_return" not in d


def test_label_field_rejection():
    rec = build_prediction_record(_run(), Horizon.T1)
    d = rec.model_dump()
    assert "label" not in d and "actual_return" not in d


# ── 11-12. duplicate / deterministic id ──
def test_duplicate_id_fail_closed():
    with pytest.raises(DuplicatePredictionIdError):
        build_prediction_dataset([_run(), _run()], horizons=[Horizon.T1])


def test_deterministic_id():
    assert build_prediction_id("SPY", T, AS_OF, Horizon.T1) == \
           build_prediction_id("SPY", T, AS_OF, Horizon.T1)
    assert len(build_prediction_id("SPY", T, AS_OF, Horizon.T1)) == 64


# ── 13-14. deterministic serialization / hash ──
def test_deterministic_serialization():
    ds1 = build_prediction_dataset([_run()], horizons=[Horizon.T1])
    ds2 = build_prediction_dataset([_run()], horizons=[Horizon.T1])
    assert ds1.records == ds2.records


def test_deterministic_dataset_hash():
    ds1 = build_prediction_dataset([_run()])
    ds2 = build_prediction_dataset([_run()])
    assert ds1.manifest.dataset_hash == ds2.manifest.dataset_hash


# ── 15. future mutation invariance ──
def test_future_mutation_invariance(monkeypatch):
    import quant_engine.features.base as fb

    ds1 = build_prediction_dataset([run_historical_t("SPY", T)], horizons=[Horizon.T1])
    h1 = ds1.manifest.dataset_hash

    def modified(frequency, as_of=None):
        frames = [pd.read_parquet(f) for f in sorted((fb.INGEST / frequency).glob("*.parquet"))]
        df = pd.concat(frames, ignore_index=True)
        if "close" in set(df["field"]):
            mask = (df["field"] == "close") & \
                   (pd.to_datetime(df["available_at"]) > pd.Timestamp("2024-06-03 23:59:59"))
            df.loc[mask, "value"] = 99999.0
        if as_of is not None:
            avail = pd.to_datetime(df["available_at"])
            df = df[avail <= pd.Timestamp(as_of)]
        wide = df.pivot_table(index="timestamp", columns="field", values="value", aggfunc="last")
        wide.index = pd.to_datetime(wide.index)
        return wide.sort_index()

    monkeypatch.setattr(fb, "load_wide", modified)
    ds2 = build_prediction_dataset([run_historical_t("SPY", T)], horizons=[Horizon.T1])
    assert ds2.manifest.dataset_hash == h1


# ── 16. probability source integrity ──
def test_probability_source_integrity():
    rec1 = build_prediction_record(_run(), Horizon.T1)
    modified = {"t1": {"p_up": 0.5, "p_flat": 0.3, "p_down": 0.2}, "t2": P5["t2"]}
    rec2 = build_prediction_record(_run(p5=modified), Horizon.T1)
    assert rec2.p_up == pytest.approx(0.5)      # 反映 P5 source value
    assert rec2.p_up != rec1.p_up


# ── 17-18. Golden records ──
def test_golden_2024_06_03():
    rec = build_prediction_record(run_historical_t("SPY", date(2024, 6, 3)), Horizon.T1)
    assert rec.p_up == pytest.approx(0.3210, abs=1e-4)
    assert rec.p_flat == pytest.approx(0.4314, abs=1e-4)
    assert rec.p_down == pytest.approx(0.2476, abs=1e-4)
    assert rec.record_status == RecordStatus.VALID


def test_golden_2020_03_16():
    rec = build_prediction_record(run_historical_t("SPY", date(2020, 3, 16)), Horizon.T1)
    assert rec.record_status == RecordStatus.VALID
    # 概率完整、未修改（和为 1）
    assert abs(rec.p_up + rec.p_flat + rec.p_down - 1.0) < 1e-6
    # directional_bias 从 P5 概率 argmax 推导（deterministic，非 regime 硬编码）
    probs = {"bullish": rec.p_up, "neutral": rec.p_flat, "bearish": rec.p_down}
    assert rec.directional_bias.value == max(probs, key=probs.get)


# ── 19. coverage accounting ──
def test_coverage_accounting():
    runs = [
        _run(prediction_date=date(2024, 6, 3)),
        _run(prediction_date=date(2024, 6, 4), status=RunStatus.PIT_VIOLATION),
        _run(prediction_date=date(2024, 6, 5), status=RunStatus.NOT_AVAILABLE),
        _run(prediction_date=date(2024, 6, 6), status=RunStatus.INVALID_TRADING_DATE),
    ]
    ds = build_prediction_dataset(runs, horizons=[Horizon.T1])
    m = ds.manifest
    assert m.expected_count == 4
    assert m.valid_count == 1
    assert m.pit_violation_count == 1
    assert m.not_available_count == 1
    assert m.rejected_count == 1


# ── 20. manifest integrity ──
def test_manifest_integrity():
    ds = build_prediction_dataset([_run()], horizons=[Horizon.T1, Horizon.T2])
    m = ds.manifest
    assert m.dataset_version == "oos-pred-1.0.0"
    assert m.oos_contract_version == "1.0.0"
    assert m.symbol_scope == ["SPY"]
    assert m.horizons == ["T+1", "T+2"]
    assert m.expected_count == 2 and m.valid_count == 2
    assert m.schema_hash and m.dataset_hash and m.manifest_hash
    assert m.builder_version == "6.3-v1"


# ── 21. schema hash ──
def test_schema_hash():
    assert compute_schema_hash() == compute_schema_hash()
    assert len(compute_schema_hash()) == 64


# ── 22. outcome-field schema guard ──
def test_outcome_field_schema_guard():
    fields = set(PredictionRecord.model_fields.keys())
    for f in FORBIDDEN_OUTCOME_FIELDS:
        assert f not in fields


# ── 23. no second probability engine ──
def test_no_second_probability_engine(monkeypatch):
    import quant_engine.probability.estimator as est

    def boom(*a, **k):
        raise AssertionError("probability estimator must not be called by builder")

    monkeypatch.setattr(est, "estimate", boom)
    rec = build_prediction_record(_run(), Horizon.T1)
    assert rec.p_up == pytest.approx(0.3210)


# ── 24. no raw future-data input ──
def test_no_raw_future_data_input():
    params = list(inspect.signature(build_prediction_record).parameters)
    assert "historical_run" in params
    for forbidden in ("raw", "market_data", "future_data", "df", "close"):
        assert forbidden not in params


# ── 25. full dataset round-trip ──
def test_full_dataset_round_trip(tmp_path):
    ds = build_prediction_dataset([_run()], horizons=[Horizon.T1])
    path = str(tmp_path / "pred.parquet")
    serialize_dataset(ds, path)
    df = pd.read_parquet(path)
    assert len(df) == 1
    assert df.iloc[0]["p_up"] == pytest.approx(0.3210)
    assert df.iloc[0]["record_status"] == "VALID"
