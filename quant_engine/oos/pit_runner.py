# -*- coding: utf-8 -*-
"""Historical PIT Runner（P7 STEP 6.2）。

给定历史交易日 T，严格按当时可获得信息重建预测时点状态：
resolve prediction_as_of → pre-ingestion PIT check → P1-P6 QuantState → post-build PIT check
→ QuantContext → validated run artifact。

不运行 LLM research / 历史批量 / thesis / 指标 / 收益。只证明历史 T 可 PIT-safe、deterministic 重建。
"""
from __future__ import annotations

from datetime import date, datetime, time

from quant_engine.data.calendar import get_default_calendar
from quant_engine.data.pit import load_pit
from quant_engine.state.builders import build_quant_state
from quant_engine.integration.tradingagents_adapter import build_quant_context, to_quant_context_string

from .contract import OOS_CONTRACT_VERSION
from .models import build_evaluation_id
from .run_models import HistoricalRunResult, RunStatus, PITAuditRecord, build_run_id
from .pit_guard import PITGuard


def resolve_prediction_as_of(prediction_date: date) -> datetime:
    """POST_CLOSE（STEP 6.1 frozen）：T 日 23:59:59（naive，与 P1 available_at 语义一致）。"""
    return datetime.combine(prediction_date, time(23, 59, 59))


def run_historical_t(symbol: str = "SPY", prediction_date: date = date(2024, 6, 3),
                     horizon: str = "T+1",
                     contract_version: str = OOS_CONTRACT_VERSION) -> HistoricalRunResult:
    """重建历史 T 的 QuantState/QuantContext，全程 PIT-safe + deterministic。"""
    run_id = build_run_id(symbol, prediction_date, horizon, contract_version)
    as_of = resolve_prediction_as_of(prediction_date)

    def _result(status, **kw):
        base = dict(
            run_id=run_id, symbol=symbol, prediction_date=prediction_date,
            prediction_as_of=as_of, horizon=horizon, status=status,
            oos_contract_version=contract_version,
        )
        base.update(kw)
        return HistoricalRunResult(**base)

    # 1. T 必须是实际 SPY 交易日（禁止 silent fallback）
    calendar = get_default_calendar()
    if not calendar.is_session(prediction_date):
        return _result(RunStatus.INVALID_TRADING_DATE)

    # 2. pre-ingestion PIT check：数据源中 available_at > as_of 的行数（不得被 pipeline 使用）
    guard = PITGuard(as_of)
    try:
        pit = load_pit()
    except Exception:
        return _result(RunStatus.NOT_AVAILABLE)
    pre_audit = guard.audit_pit_df(pit)

    # 3. P1-P6：build_quant_state 内部已按 as_of 钳制（PIT 唯一数据源头，不重造）
    try:
        state = build_quant_state(symbol, as_of)
    except Exception:
        return _result(RunStatus.NOT_AVAILABLE)

    # 4. post-build PIT check：QuantState 的 observation 不得晚于 prediction_date
    post_audit = guard.audit_quant_state(state)
    if state.market.trading_date > prediction_date:
        post_audit = PITAuditRecord(
            pit_check_status="VIOLATION", max_observation_time=state.as_of,
            max_available_at=None, max_revision_time=None, prediction_as_of=as_of,
            future_rows_detected=1, revision_rows_detected=0,
        )

    # 5. QuantContext（只读渲染，不产生未来信息）
    quant_context = to_quant_context_string(build_quant_context(symbol, as_of))

    # 6. 合并 PIT audit：pre（数据源行数）+ post（QuantState 是否被污染）
    merged_audit = PITAuditRecord(
        pit_check_status="PASS" if (pre_audit.pit_check_status == "PASS"
                                    and post_audit.pit_check_status == "PASS") else "VIOLATION",
        max_observation_time=post_audit.max_observation_time or pre_audit.max_observation_time,
        max_available_at=pre_audit.max_available_at,
        max_revision_time=pre_audit.max_revision_time,
        prediction_as_of=as_of,
        future_rows_detected=post_audit.future_rows_detected,
        revision_rows_detected=pre_audit.revision_rows_detected,
    )

    final_status = RunStatus.PIT_VIOLATION if merged_audit.pit_check_status == "VIOLATION" else RunStatus.PASS

    # 7. 概率快照（T+1/T+2，来自 P5）
    p5 = {
        "t1": {"p_up": state.probability.t1.p_up, "p_flat": state.probability.t1.p_flat,
               "p_down": state.probability.t1.p_down} if state.probability.t1 else None,
        "t2": {"p_up": state.probability.t2.p_up, "p_flat": state.probability.t2.p_flat,
               "p_down": state.probability.t2.p_down} if state.probability.t2 else None,
    }
    regime = {dim: dict(getattr(state.regime, dim))
              for dim in ("trend", "volatility", "macro", "event")}

    return _result(
        final_status,
        quant_state=state.model_dump(mode="json"),
        quant_context=quant_context,
        p4_regime=regime,
        p5_probability=p5,
        quant_state_version=state.state_version,
        renderer_version="quant_context_v1",
        source_lineage=state.lineage.model_dump(mode="json"),
        pit_audit=merged_audit,
    )
