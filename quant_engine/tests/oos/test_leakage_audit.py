# -*- coding: utf-8 -*-
"""OOS Leakage Audit 单元测试（P7 STEP 6.4）。"""
from datetime import date, datetime, timedelta

from quant_engine.oos.pit_runner import run_historical_t
from quant_engine.oos.run_models import HistoricalRunResult, RunStatus, PITAuditRecord
from quant_engine.oos.models import Horizon
from quant_engine.oos.dataset_builder import build_prediction_record, build_prediction_dataset
from quant_engine.oos.dataset_models import PredictionRecord, RecordStatus
from quant_engine.oos.leakage_models import CheckStatus
from quant_engine.oos.leakage_audit import audit_prediction_record

T = date(2024, 6, 3)
AS_OF = datetime(2024, 6, 3, 23, 59, 59)
P5 = {"t1": {"p_up": 0.3210, "p_flat": 0.4314, "p_down": 0.2476},
      "t2": {"p_up": 0.3, "p_flat": 0.4, "p_down": 0.3}}


def _run(pit_audit=None, **kw):
    base = dict(
        run_id="run-2024-06-03", symbol="SPY", prediction_date=T,
        prediction_as_of=AS_OF, horizon="T+1", status=RunStatus.PASS,
        p5_probability=P5, quant_state_version="quant-state-v1.0.0",
        renderer_version="quant_context_v1", oos_contract_version="1.0.0",
        source_lineage={"data_version": "p1_canonical_v1"},
        pit_audit=pit_audit or PITAuditRecord(pit_check_status="PASS", prediction_as_of=AS_OF),
    )
    base.update(kw)
    return HistoricalRunResult(**base)


def _rec(**kw):
    base = dict(
        prediction_id="p1", run_id="run-2024-06-03", symbol="SPY", prediction_date=T,
        prediction_as_of=AS_OF, horizon=Horizon.T1,
        p_up=0.3210, p_flat=0.4314, p_down=0.2476,
        quant_state_version="quant-state-v1.0.0", renderer_version="quant_context_v1",
        oos_contract_version="1.0.0", source_lineage={"data_version": "p1_canonical_v1"},
    )
    base.update(kw)
    return PredictionRecord(**base)


def _check(result, name):
    return next(c for c in result.checks if c.name == name)


def test_l1_pass():
    hr = _run()
    r = audit_prediction_record(_rec(), hr)
    assert _check(r, "L1 Temporal").status == CheckStatus.PASS


def test_l1_fail_future_available():
    leaky = PITAuditRecord(pit_check_status="PASS", prediction_as_of=AS_OF,
                           max_available_at=AS_OF + timedelta(days=1))
    r = audit_prediction_record(_rec(), _run(pit_audit=leaky))
    assert _check(r, "L1 Temporal").status == CheckStatus.FAIL


def test_l2_pass():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L2 Revision").status == CheckStatus.PASS


def test_l2_fail_future_revision():
    leaky = PITAuditRecord(pit_check_status="PASS", prediction_as_of=AS_OF,
                           max_revision_time=AS_OF + timedelta(days=2))
    r = audit_prediction_record(_rec(), _run(pit_audit=leaky))
    assert _check(r, "L2 Revision").status == CheckStatus.FAIL


def test_l3_pass_no_outcome():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L3 Label").status == CheckStatus.PASS


def test_l4_pass_no_global_state():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L4 Cross-Sample").status == CheckStatus.PASS


def test_l5_not_verified_static_boundary():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L5 Agent Research").status == CheckStatus.NOT_VERIFIED


def test_l6_pass_lineage():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L6 QuantState").status == CheckStatus.PASS


def test_l6_fail_missing_lineage():
    r = audit_prediction_record(_rec(source_lineage=None), _run())
    assert _check(r, "L6 QuantState").status == CheckStatus.FAIL


def test_l7_pass_renderer():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L7 QuantContext").status == CheckStatus.PASS


def test_l8_not_applicable_no_thesis_text():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L8 Thesis").status == CheckStatus.NOT_APPLICABLE


def test_l9_pass_config_fingerprint():
    r = audit_prediction_record(_rec(), _run())
    assert _check(r, "L9 Tuning").status == CheckStatus.PASS


def test_l9_fail_config_drift():
    r = audit_prediction_record(_rec(oos_contract_version="9.9.9"), _run())
    assert _check(r, "L9 Tuning").status == CheckStatus.FAIL


def test_overall_fail_priority():
    leaky = PITAuditRecord(pit_check_status="PASS", prediction_as_of=AS_OF,
                           max_available_at=AS_OF + timedelta(days=1))
    r = audit_prediction_record(_rec(), _run(pit_audit=leaky))
    assert r.overall_status == CheckStatus.FAIL
    assert len(r.violations) >= 1


def test_overall_not_verified_when_l5():
    # 有 historical_run 时 L1/L2/L6/L7 可验证，但 L5 仍 NOT_VERIFIED → overall NOT_VERIFIED
    r = audit_prediction_record(_rec(), _run())
    assert r.overall_status == CheckStatus.NOT_VERIFIED


def test_audit_id_deterministic():
    r1 = audit_prediction_record(_rec(), _run())
    r2 = audit_prediction_record(_rec(), _run())
    assert r1.audit_id == r2.audit_id
    assert len(r1.audit_id) == 64


def test_real_golden_record_audit():
    hr = run_historical_t("SPY", T)
    rec = build_prediction_record(hr, Horizon.T1)
    r = audit_prediction_record(rec, hr)
    # 真实 record：L1/L2/L3/L6/L7/L9 PASS；L5 NOT_VERIFIED；L8 NOT_APPLICABLE
    assert _check(r, "L1 Temporal").status == CheckStatus.PASS
    assert _check(r, "L2 Revision").status == CheckStatus.PASS
    assert _check(r, "L3 Label").status == CheckStatus.PASS
    assert _check(r, "L6 QuantState").status == CheckStatus.PASS
    assert _check(r, "L7 QuantContext").status == CheckStatus.PASS
    assert _check(r, "L9 Tuning").status == CheckStatus.PASS
    assert r.overall_status == CheckStatus.NOT_VERIFIED
