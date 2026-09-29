# -*- coding: utf-8 -*-
"""OOS Leakage audit independence / serialization / hash tests（P7 STEP 6.4）。"""
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quant_engine.oos.pit_runner import run_historical_t
from quant_engine.oos.run_models import HistoricalRunResult, RunStatus, PITAuditRecord
from quant_engine.oos.models import Horizon
from quant_engine.oos.dataset_builder import (
    build_prediction_record, build_prediction_dataset, serialize_dataset,
)
from quant_engine.oos.dataset_models import PredictionRecord, RecordStatus, FORBIDDEN_OUTCOME_FIELDS
from quant_engine.oos.leakage_models import CheckStatus
from quant_engine.oos.leakage_audit import audit_prediction_record

T = date(2024, 6, 3)
AS_OF = datetime(2024, 6, 3, 23, 59, 59)
P5 = {"t1": {"p_up": 0.3210, "p_flat": 0.4314, "p_down": 0.2476},
      "t2": {"p_up": 0.3, "p_flat": 0.4, "p_down": 0.3}}


def _run(pit_audit=None, **kw):
    base = dict(
        run_id="r", symbol="SPY", prediction_date=T, prediction_as_of=AS_OF,
        horizon="T+1", status=RunStatus.PASS, p5_probability=P5,
        quant_state_version="quant-state-v1.0.0", renderer_version="quant_context_v1",
        oos_contract_version="1.0.0", source_lineage={"data_version": "p1_canonical_v1"},
        pit_audit=pit_audit or PITAuditRecord(pit_check_status="PASS", prediction_as_of=AS_OF),
    )
    base.update(kw)
    return HistoricalRunResult(**base)


def test_audit_independence_bad_dataset():
    """audit 不信任 record.pit_status，重新验证 source lineage timestamps。"""
    leaky_pit = PITAuditRecord(pit_check_status="PASS", prediction_as_of=AS_OF,
                               max_available_at=AS_OF + timedelta(days=1))
    hr = _run(pit_audit=leaky_pit)
    # BAD builder：篡改 pit_status="PASS"（本该 VIOLATION），但底层 source 泄漏
    rec = PredictionRecord(
        prediction_id="p1", run_id="r", symbol="SPY", prediction_date=T,
        prediction_as_of=AS_OF, horizon=Horizon.T1,
        p_up=0.321, p_flat=0.4314, p_down=0.2476,
        quant_state_version="v", renderer_version="v", oos_contract_version="1.0.0",
        source_lineage={"data_version": "p1_canonical_v1"},
        pit_status="PASS", record_status=RecordStatus.VALID,
    )
    result = audit_prediction_record(rec, hr)
    assert result.overall_status == CheckStatus.FAIL
    assert any(v.leakage_type == "L1_TEMPORAL" for v in result.violations)


def test_serialization_audit(tmp_path):
    ds = build_prediction_dataset([_run()], horizons=[Horizon.T1])
    path = str(tmp_path / "pred.parquet")
    serialize_dataset(ds, path)
    df = pd.read_parquet(path)
    # system-owned fields 不因 serialize→deserialize 变化
    rec = ds.records[0]
    assert df.iloc[0]["prediction_id"] == rec.prediction_id
    assert df.iloc[0]["prediction_as_of"] == rec.prediction_as_of.isoformat()
    assert df.iloc[0]["p_up"] == pytest.approx(rec.p_up)
    assert df.iloc[0]["p_flat"] == pytest.approx(rec.p_flat)
    assert df.iloc[0]["p_down"] == pytest.approx(rec.p_down)
    assert df.iloc[0]["horizon"] == "T+1"
    assert df.iloc[0]["pit_status"] == "PASS"


def test_dataset_hash_audit():
    ds1 = build_prediction_dataset([_run()], horizons=[Horizon.T1])
    ds2 = build_prediction_dataset([_run()], horizons=[Horizon.T1])
    assert ds1.manifest.dataset_hash == ds2.manifest.dataset_hash


def test_false_positive_control():
    """audit 用 typed schema（exact match），不用粗暴 substring。"""
    rec = build_prediction_record(_run(), Horizon.T1)
    # "positive"/"negative" 含 "iv" 子串，但 audit 不应误判（L3 用 FORBIDDEN_OUTCOME_FIELDS 精确匹配）
    result = audit_prediction_record(rec, _run())
    l3 = next(c for c in result.checks if c.name == "L3 Label")
    assert l3.status == CheckStatus.PASS
    # schema 检查是 exact field name，不是 substring
    assert "iv" not in FORBIDDEN_OUTCOME_FIELDS


def test_no_strategy_leakage():
    """audit 不得引入 options/strike/delta/gamma/theta/kelly/position_size/pnl。"""
    import inspect
    import quant_engine.oos.leakage_audit as la
    src = inspect.getsource(la)
    for forbidden in ("strike", "delta", "gamma", "theta", "kelly", "position_size", "pnl"):
        assert forbidden not in src.lower(), f"strategy field {forbidden} 泄漏进 audit"
