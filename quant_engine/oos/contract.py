# -*- coding: utf-8 -*-
"""OOS Evaluation Contract v1.0.0（P7 STEP 6.1）。

本模块只冻结 contract 常量与语义，不运行任何历史批量、不生成预测数据集、
不跑 Multi-Agent 历史回测。用于后续 STEP 6.2+ 的样本外预测质量评估。

所有值均为 frozen 语义；修改需新版本（immutable after lock）。
"""
from __future__ import annotations

OOS_CONTRACT_VERSION = "1.0.0"
OOS_CONTRACT_NAME = "OOS Evaluation Contract"

# ── 1. Prediction time（正式 cutoff，从 P1 PIT semantics 确认，非自行假定）──
# P1 data/pit.py：available_at = 交易日 23:59:59 UTC（收盘后可用）。
# 「判断 T 状态」能看到 T 收盘，看不到 T+1。
# 因此正式 prediction_as_of = T 日收盘后。
PREDICTION_AS_OF_RULE = "T 日收盘后（as_of = T 日 23:59:59 UTC，等价于 T 日收盘数据 available_at）"
PREDICTION_AS_OF_CLASS = "POST_CLOSE"   # 选项 C：收盘后信息（非盘前/盘中）

# ── 2. PIT Boundary Contract ──
PIT_BOUNDARY_RULE = "available_at <= prediction_as_of → eligible；> → forbidden"
# 四时间字段语义（P1 data/pit.py）
TIME_FIELDS = ("observation_time", "published_at", "available_at", "revision_time")
REVISION_RULE = "revision_time > prediction_as_of 的修订值禁止进入预测"

# ── 3. Trading Day Calendar ──
CALENDAR_RULE = "T+1/T+2 按 SPY 实际交易日计算（TradingCalendar.next_session），禁止 calendar day +1"

# ── 4. Temporal split（源自 P5 frozen pipeline.TEMPORAL_SPLIT，无定义差异）──
OOS_TEMPORAL_SPLIT = {
    "train": ("2013-01-01", "2020-12-31"),
    "validation": ("2021-01-01", "2023-12-31"),
    "test": ("2024-01-01", "2026-09-25"),
}
SPLIT_SOURCE_NOTE = "与 P5 frozen probability/pipeline.py TEMPORAL_SPLIT 一致，无定义差异"

# ── 5. Prediction object：probability 来源 ──
PROBABILITY_SOURCE = "P5 ProbabilityEstimate（唯一来源）"
PROBABILITY_SUM_RULE = "p_up + p_flat + p_down = 1（tolerance 1e-6）"

# ── 6. Label reference（P3 frozen，不重新发明）──
LABEL_REFERENCE = "P3 frozen labels（t1_up_flat_down / t2_up_flat_down）"
LABEL_THRESHOLD_RULE = "threshold = 0.5 × realized_vol_20(T) / sqrt(252)；fwd = close[T+n]/close[T] − 1"
LABEL_OUTCOME_RULE = "UP if fwd > +threshold；DOWN if fwd < −threshold；else FLAT；endpoint 缺失 → 不生成 label（非 FLAT）"

# ── 7. Prediction vs Outcome boundary ──
PREDICTION_OUTCOME_BOUNDARY = (
    "T 时刻信息 → prediction pipeline（QuantState/Context/Research/Thesis）；"
    "T+1/T+2 市场数据 → 仅 evaluation label。禁止 outcome 反向进入 prediction pipeline。"
)

# ── 8. Metrics（P5 frozen）──
PRIMARY_METRICS = ("log_loss", "brier")                      # 三分类 UP/FLAT/DOWN，沿用 P5
SECONDARY_METRICS = ("accuracy", "directional_accuracy")     # secondary / descriptive，非核心

# ── 9. Baselines（P5 frozen）──
BASELINE_UNCONDITIONAL = "baseline_unconditional"            # 无条件历史分布，与 P5 一致
BASELINE_UNIFORM_REFERENCE = "uniform (log(3)=1.0986 / Brier=0.6667)"  # 参考基线，非新增

# ── 10. Missing data semantics（禁止 None→0/neutral/average）──
MISSING_DATA_STATUSES = (
    "VALID", "INSUFFICIENT_SAMPLE", "NOT_AVAILABLE",
    "NOT_EVALUABLE", "PIT_VIOLATION", "INVALID",
)
PIT_VIOLATION_NOTE = "PIT_VIOLATION = 预测侧发现未来信息进入 T pipeline；不得简单 skip，须记为严重 audit failure"

# ── 11. Leakage taxonomy（正式定义，L1-L9）──
LEAKAGE_TAXONOMY = {
    "L1_temporal": "T 之后的数据进入 T prediction",
    "L2_revision": "未来 revision value 被用于历史 prediction",
    "L3_label": "T+1/T+2 outcome 进入 prediction pipeline",
    "L4_cross_sample": "前一历史样本的 outcome/metric 影响后续 prediction",
    "L5_agent_research": "Agent 在 T research 时读取 T 之后信息",
    "L6_quantstate": "QuantState(T) 含未来 observation/availability",
    "L7_context": "QuantContext(T) 含未来信息",
    "L8_thesis": "TradingThesis(T) 使用 outcome-derived information",
    "L9_tuning": "用 OOS 结果调 prompt/threshold/parameter/model/feature/rule 后仍把同一 OOS 当未知评估",
}

# ── 12. 明确排除 ──
NON_SCOPE_NOTE = (
    "Prediction Quality ≠ strategy profitability；禁止把 prediction accuracy 解释为 "
    "SPY vertical spread 盈利，禁止 p_up → option trade → PnL。STEP 6 只回答预测概率是否具信息价值。"
)

# ── 13. 历史 OOS ≠ 训练 LLM ──
TRAINING_BOUNDARY = (
    "Historical OOS evaluation ≠ 用历史结果训练 LLM。OOS 样本的 outcome/label/metric "
    "不得反馈给后续尚未执行的历史预测（禁止 run T → 看结果 → 改 prompt → run T+1）。"
)
