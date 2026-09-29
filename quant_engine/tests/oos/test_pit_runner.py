# -*- coding: utf-8 -*-
"""Historical PIT Runner 测试（P7 STEP 6.2）。"""
from datetime import date

import pytest

from quant_engine.oos.pit_runner import run_historical_t, resolve_prediction_as_of
from quant_engine.oos.run_models import RunStatus


def test_normal_trading_day():
    r = run_historical_t("SPY", date(2024, 6, 3))
    assert r.status == RunStatus.PASS
    assert r.quant_state["market"]["trading_date"] == "2024-06-03"
    assert r.pit_audit.future_rows_detected == 0


def test_weekend():
    r = run_historical_t("SPY", date(2024, 6, 1))  # 周六
    assert r.status == RunStatus.INVALID_TRADING_DATE


def test_holiday():
    r = run_historical_t("SPY", date(2024, 7, 4))  # 独立日
    assert r.status == RunStatus.INVALID_TRADING_DATE


def test_month_start():
    r = run_historical_t("SPY", date(2024, 6, 3))
    assert r.status == RunStatus.PASS


def test_month_end():
    r = run_historical_t("SPY", date(2024, 6, 28))
    assert r.status == RunStatus.PASS


def test_macro_release_day():
    # 宏观数据发布日（非农等）仍是正常交易日
    r = run_historical_t("SPY", date(2024, 6, 7))
    assert r.status == RunStatus.PASS


def test_golden_2024_06_03():
    r = run_historical_t("SPY", date(2024, 6, 3))
    assert r.status == RunStatus.PASS
    # P5 T1 概率（frozen Golden）
    t1 = r.p5_probability["t1"]
    assert t1["p_up"] == pytest.approx(0.3210, abs=1e-4)
    assert t1["p_flat"] == pytest.approx(0.4314, abs=1e-4)
    assert t1["p_down"] == pytest.approx(0.2476, abs=1e-4)
    # P4 regime（frozen Golden）
    assert r.p4_regime["trend"]["bull_trend"] == pytest.approx(0.8333, abs=1e-4)
    assert r.p4_regime["volatility"]["low_volatility"] == pytest.approx(1.0, abs=1e-6)
    assert r.quant_state_version == "quant-state-v1.0.0"


def test_golden_2020_03_16():
    r = run_historical_t("SPY", date(2020, 3, 16))
    assert r.status == RunStatus.PASS
    # 2020-03-16 COVID 崩盘：bear regime + high volatility（frozen Golden）
    assert r.p4_regime["trend"]["bear_trend"] >= 0.8
    assert r.p4_regime["volatility"]["high_volatility"] >= 0.5


def test_run_id_deterministic():
    r1 = run_historical_t("SPY", date(2024, 6, 3))
    r2 = run_historical_t("SPY", date(2024, 6, 3))
    assert r1.run_id == r2.run_id


def test_prediction_as_of_rule():
    as_of = resolve_prediction_as_of(date(2024, 6, 3))
    assert as_of.hour == 23 and as_of.minute == 59 and as_of.second == 59
    assert as_of.date() == date(2024, 6, 3)
