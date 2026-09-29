# -*- coding: utf-8 -*-
"""OOS Evaluation Contract tests（P7 STEP 6.1，20 cases）。"""
from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from quant_engine.data.calendar import TradingCalendar
from quant_engine.oos import (
    Horizon, DataStatus, EvaluationUnit, PredictionRecord, OutcomeRecord,
    ModelProvenanceRef, build_evaluation_id,
)
from quant_engine.oos.contract import (
    OOS_CONTRACT_VERSION, OOS_TEMPORAL_SPLIT, PRIMARY_METRICS, SECONDARY_METRICS,
    BASELINE_UNCONDITIONAL, LEAKAGE_TAXONOMY, MISSING_DATA_STATUSES,
)
from quant_engine.oos.validation import (
    t_plus_n, is_pit_eligible, is_revision_forbidden, classify_outcome,
    evaluation_id_is_deterministic,
)

T = date(2024, 6, 3)
AS_OF = datetime(2024, 6, 3, 23, 59, 59)


def _calendar() -> TradingCalendar:
    # 小日历：跳过 7/4（假日）+ 周末
    return TradingCalendar({
        date(2024, 7, 1), date(2024, 7, 2), date(2024, 7, 3),
        date(2024, 7, 5), date(2024, 7, 8), date(2024, 7, 9),
    })


def _unit(**kw):
    base = dict(
        evaluation_id=build_evaluation_id("SPY", T, Horizon.T1),
        symbol="SPY", prediction_date=T, prediction_as_of=AS_OF, horizon=Horizon.T1,
        label_version="v1", quant_state_version="quant-state-v1.0.0",
        renderer_version="quant_context_v1", thesis_contract_version="thesis-schema-v1",
    )
    base.update(kw)
    return EvaluationUnit(**base)


def _pred(**kw):
    base = dict(
        prediction_date=T, symbol="SPY", horizon=Horizon.T1,
        p_up=0.3210, p_flat=0.4314, p_down=0.2476,
        directional_bias="neutral", confidence=0.8, thesis_id="t-1",
        run_id="r-1", quant_state_version="quant-state-v1.0.0",
        renderer_version="quant_context_v1",
        model_provenance=ModelProvenanceRef(
            provider="deepseek", model="deepseek-v4-pro", temperature=0.2,
            prompt_version="research_prompt_v1", agent_version="quant_analyst_v1", run_id="r-1"),
    )
    base.update(kw)
    return PredictionRecord(**base)


# ── 1. valid contract ──
def test_valid_contract():
    u = _unit()
    assert u.contract_version == OOS_CONTRACT_VERSION
    assert u.horizon == Horizon.T1
    p = _pred()
    assert abs(p.p_up + p.p_flat + p.p_down - 1.0) < 1e-6


# ── 2. deterministic evaluation_id ──
def test_deterministic_evaluation_id():
    assert evaluation_id_is_deterministic("SPY", T, Horizon.T1)
    a = build_evaluation_id("SPY", T, Horizon.T1)
    b = build_evaluation_id("SPY", T, Horizon.T1)
    assert a == b


# ── 3. invalid horizon ──
def test_invalid_horizon():
    with pytest.raises(ValidationError):
        _unit(horizon="T+3")


# ── 4. invalid symbol ──
def test_invalid_symbol():
    with pytest.raises(ValidationError):
        _pred(symbol="")


# ── 5. invalid probability sum ──
def test_invalid_probability_sum():
    with pytest.raises(ValidationError):
        _pred(p_up=0.5, p_flat=0.5, p_down=0.5)


# ── 6. invalid PIT boundary ──
def test_invalid_pit_boundary():
    # available_at 在 as_of 之后 → ineligible
    assert not is_pit_eligible(datetime(2024, 6, 4, 0, 0, 0), AS_OF)
    assert is_pit_eligible(datetime(2024, 6, 3, 23, 59, 59), AS_OF)


# ── 7. future availability rejection ──
def test_future_availability_rejection():
    future = datetime(2024, 6, 5, 23, 59, 59)
    assert not is_pit_eligible(future, AS_OF)


# ── 8. future revision rejection ──
def test_future_revision_rejection():
    future_rev = datetime(2024, 6, 10, 0, 0, 0)
    assert is_revision_forbidden(future_rev, AS_OF)
    assert not is_revision_forbidden(None, AS_OF)


# ── 9. T+1/T+2 trading-day calculation ──
def test_t_plus_n_trading_day():
    cal = _calendar()
    assert t_plus_n(cal, date(2024, 7, 3), 1) == date(2024, 7, 5)   # 跳过 7/4 假日
    assert t_plus_n(cal, date(2024, 7, 3), 2) == date(2024, 7, 8)   # 再跳过周末


# ── 10. weekend handling ──
def test_weekend_handling():
    cal = _calendar()
    # 周五 T+1 = 周一
    assert t_plus_n(cal, date(2024, 7, 5), 1) == date(2024, 7, 8)


# ── 11. holiday handling ──
def test_holiday_handling():
    cal = _calendar()
    # 7/4 不是 session
    assert not cal.is_session(date(2024, 7, 4))
    # T=7/3 周三，T+1 跳过 7/4 → 7/5
    assert t_plus_n(cal, date(2024, 7, 3), 1) == date(2024, 7, 5)


# ── 12. NOT_EVALUABLE outcome ──
def test_not_evaluable_outcome():
    assert classify_outcome(None, None) == DataStatus.NOT_EVALUABLE
    assert classify_outcome(0.01, None) == DataStatus.NOT_EVALUABLE


# ── 13. PIT_VIOLATION classification ──
def test_pit_violation_classification():
    assert classify_outcome(0.01, "UP", pit_violated=True) == DataStatus.PIT_VIOLATION


# ── 14. label/prediction separation ──
def test_label_prediction_separation():
    # label 是 outcome 侧对象，prediction 是 prediction 侧对象，二者身份不同
    p = _pred()
    o = OutcomeRecord(evaluation_id=build_evaluation_id("SPY", T, Horizon.T1),
                      symbol="SPY", horizon=Horizon.T1, actual_return=0.005, label="UP")
    assert p.prediction_date == T
    # label 使用未来数据合法（仅 evaluation），但不得进入 prediction：prediction 无 outcome 字段
    p_dump = p.model_dump()
    assert "actual_return" not in p_dump
    assert "label" not in p_dump
    assert o.label == "UP"


# ── 15. OOS split immutability ──
def test_oos_split_immutability():
    assert OOS_TEMPORAL_SPLIT["train"] == ("2013-01-01", "2020-12-31")
    assert OOS_TEMPORAL_SPLIT["validation"] == ("2021-01-01", "2023-12-31")
    assert OOS_TEMPORAL_SPLIT["test"] == ("2024-01-01", "2026-09-25")


# ── 16. metric definition consistency with P5 ──
def test_metric_consistency():
    assert set(PRIMARY_METRICS) == {"log_loss", "brier"}
    assert "accuracy" in SECONDARY_METRICS or "directional_accuracy" in SECONDARY_METRICS


# ── 17. baseline definition consistency ──
def test_baseline_consistency():
    assert BASELINE_UNCONDITIONAL == "baseline_unconditional"


# ── 18. provenance requirement ──
def test_provenance_requirement():
    p = _pred()
    mp = p.model_provenance
    assert mp.provider and mp.model and mp.run_id and mp.prompt_version and mp.agent_version


# ── 19. contract version requirement ──
def test_contract_version_requirement():
    u = _unit()
    assert u.contract_version == OOS_CONTRACT_VERSION == "1.0.0"
    assert len(LEAKAGE_TAXONOMY) == 9
    assert set(MISSING_DATA_STATUSES) == {
        "VALID", "INSUFFICIENT_SAMPLE", "NOT_AVAILABLE",
        "NOT_EVALUABLE", "PIT_VIOLATION", "INVALID",
    }


# ── 20. deterministic serialization ──
def test_deterministic_serialization():
    p1 = _pred()
    p2 = _pred()
    assert p1.model_dump(mode="json") == p2.model_dump(mode="json")
