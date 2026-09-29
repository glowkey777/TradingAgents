# -*- coding: utf-8 -*-
"""OOS Prediction Dataset Builder（P7 STEP 6.3）。

职责：validate / extract / normalize schema / serialize / manifest。
不重新计算 P1-P6，不读取未来 market data，不生成第二套 Quant Engine result。
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from .contract import OOS_CONTRACT_VERSION
from .models import DirectionalBias, Horizon
from .run_models import HistoricalRunResult, RunStatus
from .dataset_models import (
    PredictionRecord, PredictionDataset, DatasetManifest, RecordStatus,
    build_prediction_id, compute_schema_hash, compute_dataset_hash, _sha256,
)

BUILDER_VERSION = "6.3-v1"


class DuplicatePredictionIdError(Exception):
    """prediction_id 重复 → fail closed。"""


def _map_status(run_status: RunStatus) -> RecordStatus:
    return {
        RunStatus.PASS: RecordStatus.VALID,
        RunStatus.INVALID_TRADING_DATE: RecordStatus.NOT_EVALUABLE,
        RunStatus.PIT_VIOLATION: RecordStatus.PIT_VIOLATION,
        RunStatus.NOT_AVAILABLE: RecordStatus.NOT_AVAILABLE,
        RunStatus.INVALID: RecordStatus.INVALID,
    }[run_status]


def _derive_bias(p_up: float, p_flat: float, p_down: float) -> DirectionalBias:
    probs = {DirectionalBias.BULLISH: p_up,
             DirectionalBias.NEUTRAL: p_flat,
             DirectionalBias.BEARISH: p_down}
    return max(probs, key=probs.get)


def build_prediction_record(historical_run: HistoricalRunResult,
                            horizon: Horizon,
                            contract_version: str = OOS_CONTRACT_VERSION) -> PredictionRecord:
    """从 HistoricalRunResult 提取 P5 概率，生成 PredictionRecord（不重算）。"""
    prediction_id = build_prediction_id(
        historical_run.symbol, historical_run.prediction_date,
        historical_run.prediction_as_of, horizon, contract_version,
    )
    record_status = _map_status(historical_run.status)
    pit_status = historical_run.pit_audit.pit_check_status if historical_run.pit_audit else "PASS"

    # 非 VALID 状态：fail-closed，保留 audit（不 drop，不填充假概率）
    if record_status != RecordStatus.VALID:
        return PredictionRecord(
            prediction_id=prediction_id,
            run_id=historical_run.run_id,
            symbol=historical_run.symbol,
            prediction_date=historical_run.prediction_date,
            prediction_as_of=historical_run.prediction_as_of,
            horizon=horizon,
            p_up=0.0, p_flat=0.0, p_down=0.0,
            quant_state_version=historical_run.quant_state_version,
            renderer_version=historical_run.renderer_version,
            oos_contract_version=contract_version,
            source_lineage=historical_run.source_lineage,
            pit_status=pit_status,
            record_status=record_status,
            failure_reason=f"historical_run.status={historical_run.status.value}",
        )

    # VALID：概率必须来自 P5（exact-source）
    horizon_key = "t1" if horizon == Horizon.T1 else "t2"
    probs = (historical_run.p5_probability or {}).get(horizon_key)
    if probs is None:
        return PredictionRecord(
            prediction_id=prediction_id, run_id=historical_run.run_id,
            symbol=historical_run.symbol, prediction_date=historical_run.prediction_date,
            prediction_as_of=historical_run.prediction_as_of, horizon=horizon,
            p_up=0.0, p_flat=0.0, p_down=0.0,
            quant_state_version=historical_run.quant_state_version,
            renderer_version=historical_run.renderer_version,
            oos_contract_version=contract_version,
            source_lineage=historical_run.source_lineage,
            pit_status=pit_status, record_status=RecordStatus.NOT_AVAILABLE,
            failure_reason=f"P5 probability {horizon.value} not available",
        )

    p_up, p_flat, p_down = probs["p_up"], probs["p_flat"], probs["p_down"]
    return PredictionRecord(
        prediction_id=prediction_id,
        run_id=historical_run.run_id,
        symbol=historical_run.symbol,
        prediction_date=historical_run.prediction_date,
        prediction_as_of=historical_run.prediction_as_of,
        horizon=horizon,
        p_up=p_up, p_flat=p_flat, p_down=p_down,
        directional_bias=_derive_bias(p_up, p_flat, p_down),
        confidence=max(p_up, p_flat, p_down),
        confidence_level="P5_max_probability",
        quant_state_version=historical_run.quant_state_version,
        renderer_version=historical_run.renderer_version,
        oos_contract_version=contract_version,
        source_lineage=historical_run.source_lineage,
        pit_status=pit_status,
        record_status=record_status,
    )


def build_prediction_dataset(historical_runs: list[HistoricalRunResult],
                             horizons: list[Horizon] | None = None,
                             contract_version: str = OOS_CONTRACT_VERSION) -> PredictionDataset:
    """从 HistoricalRunResult 序列构建 PredictionDataset（prediction-side only）。"""
    if horizons is None:
        horizons = [Horizon.T1, Horizon.T2]

    records: list[PredictionRecord] = []
    for run in historical_runs:
        for h in horizons:
            records.append(build_prediction_record(run, h, contract_version))

    # duplicate fail-closed
    seen: set[str] = set()
    for rec in records:
        if rec.prediction_id in seen:
            raise DuplicatePredictionIdError(f"duplicate prediction_id={rec.prediction_id}")
        seen.add(rec.prediction_id)

    # deterministic ordering：date ASC, symbol ASC, horizon ASC, id ASC
    records.sort(key=lambda r: (r.prediction_date.isoformat(), r.symbol, r.horizon.value, r.prediction_id))

    valid = [r for r in records if r.record_status == RecordStatus.VALID]
    pit_violation = [r for r in records if r.record_status == RecordStatus.PIT_VIOLATION]
    not_available = [r for r in records if r.record_status == RecordStatus.NOT_AVAILABLE]
    rejected = [r for r in records if r.record_status in (RecordStatus.INVALID, RecordStatus.NOT_EVALUABLE)]

    dates = [r.prediction_date for r in records]
    symbols = sorted({r.symbol for r in records})
    qsv = records[0].quant_state_version if records else ""
    rv = records[0].renderer_version if records else ""

    schema_hash = compute_schema_hash()
    dataset_hash = compute_dataset_hash(records)

    manifest = DatasetManifest(
        dataset_version=f"oos-pred-{contract_version}",
        oos_contract_version=contract_version,
        symbol_scope=symbols,
        start_date=min(dates) if dates else None,
        end_date=max(dates) if dates else None,
        horizons=[h.value for h in horizons],
        expected_count=len(historical_runs) * len(horizons),
        valid_count=len(valid),
        rejected_count=len(rejected),
        not_available_count=len(not_available),
        pit_violation_count=len(pit_violation),
        quant_state_version=qsv,
        renderer_version=rv,
        builder_version=BUILDER_VERSION,
        schema_hash=schema_hash,
        dataset_hash=dataset_hash,
        manifest_hash="",
        created_at="",
    )
    # manifest_hash 不含 created_at（created_at 不影响 identity）
    manifest.manifest_hash = _sha256(manifest.model_dump(exclude={"created_at"}, mode="json"))

    return PredictionDataset(
        dataset_version=manifest.dataset_version,
        records=records,
        manifest=manifest,
    )


def serialize_dataset(dataset: PredictionDataset, path: str) -> None:
    """canonical serialization（Parquet）。nested dict → json string。"""
    rows = []
    for rec in dataset.records:
        d = rec.model_dump(mode="json")
        d["source_lineage"] = json.dumps(d["source_lineage"], sort_keys=True) if d["source_lineage"] else None
        d["model_provenance"] = json.dumps(d["model_provenance"], sort_keys=True) if d["model_provenance"] else None
        rows.append(d)
    pd.DataFrame(rows).to_parquet(path, index=False)
