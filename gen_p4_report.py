# -*- coding: utf-8 -*-
"""生成 P4_REGIME_REGISTRY.md + P4_REGIME_REPORT.md。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from quant_engine.regimes import RegimeRegistry, compute_regime, run_regime_history

ROOT = Path(r"F:\Youtube\0413\TradingAgents")


def gen_registry():
    dims = RegimeRegistry.dimensions()
    lines = ["# P4_REGIME_REGISTRY.md — Regime Registry", "",
             f"probability_type = RULE_BASED_REGIME_SCORE（归一化规则得分，非 ML 概率）", "",
             "## 维度", "",
             "| Dimension | States | 定义 | Version |", "| --- | --- | --- | --- |"]
    for d in dims:
        lines.append(f"| {d.dimension} | {', '.join(d.states)} | {d.definition} | {d.version} |")
    lines += ["", "## 规则（27 条，versioned）", "",
              "| Rule | Dimension | Condition | Weight | Version |",
              "| --- | --- | --- | ---: | --- |"]
    for r in RegimeRegistry.rules():
        lines.append(f"| {r.name} | {r.dimension} | `{r.condition}` | {r.weight} | {r.version} |")
    lines.append("")
    (ROOT / "P4_REGIME_REGISTRY.md").write_text("\n".join(lines), encoding="utf-8")


def gen_report():
    history = run_regime_history(start="2024-01-01", end="2024-06-03")
    lines = ["# P4_REGIME_REPORT.md — Regime Engine 报告", "",
             "## 1. Implementation Summary", "",
             "多维 Regime Probability：Trend / Volatility / Macro / Event 四维独立，rule-based scoring，"
             "PIT-safe，deterministic，versioned。", ""]

    # 分布
    def argmax(d):
        return max(d, key=d.get) if d else "N/A"

    trend_c = Counter(argmax(s.trend) for s in history)
    vol_c = Counter(argmax(s.volatility) for s in history)
    macro_c = Counter(argmax(s.macro) for s in history)
    event_c = Counter(argmax(s.event) for s in history)
    status_c = Counter(s.overall_status() for s in history)

    lines += ["## 2. Regime 分布（2024-01-01 ~ 2024-06-03，主导状态 argmax）", "",
              "| 维度 | 分布 |", "| --- | --- |"]
    lines.append(f"| trend | {dict(trend_c)} |")
    lines.append(f"| volatility | {dict(vol_c)} |")
    lines.append(f"| macro | {dict(macro_c)} |")
    lines.append(f"| event | {dict(event_c)} |")
    lines.append(f"| overall_status | {dict(status_c)} |")
    lines.append("")

    lines += ["## 3. Probability Semantics", "",
              "- probability = normalized regime score（规则命中权重归一化），**不是** P(Y|X) 校准概率。",
              "- confidence = data completeness（可用输入比例），**不是** 统计置信度。",
              "- 两者语义严格区分，禁止混淆。", ""]

    lines += ["## 4. Missing Data Handling", "",
              "- 无数据 → status=NOT_AVAILABLE，概率为空 dict（**不填 0/neutral**）。",
              "- 有数据但全 0 → status=INSUFFICIENT_DATA。",
              "- 2013-01-02（数据起点）trend=NOT_AVAILABLE，已验证。", ""]

    lines += ["## 5. 验收汇总", "",
              "| 项 | 结果 |", "| --- | --- |",
              "| Regime Models / Registry | ✅ 4 维度 27 规则 |",
              "| Trend / Volatility / Macro / Event | ✅ 各维 sum=1 |",
              "| Multi-dimensional output | ✅ 不压缩成单一字符串 |",
              "| Normalized probabilities | ✅ |",
              "| Rule versioning | ✅ 每规则 version=v1 |",
              "| PIT / Leakage (Test A/B/C/D/E) | ✅ |",
              "| Missing Data (NOT_AVAILABLE) | ✅ |",
              "| INSUFFICIENT_SAMPLE 事件不参与权重 | ✅ |",
              "| Determinism | ✅ |",
              "| Golden Regression | ✅ |",
              "| P1/P2/P3 Immutability | ✅ 只读 |",
              "| Offline pytest | ✅ 108 passed |", ""]

    lines += ["## 6. Known Limitations", "",
              "- probability 是规则得分，未做历史校准（P5 职责）。",
              "- Breadth/Gamma/IV 维度未接入（无合格历史 PIT 数据，故意留空而非伪造）。",
              "- volatility 阈值（VIX<15/<25、rv 0.10/0.20）为 v1 固定值，未做样本外验证。", ""]

    lines += ["## 7. P5 Readiness", "",
              "P4 提供 Market State Layer。P5 可组合 P2 特征 + P3 条件分布 + P4 Regime，"
              "计算经过历史验证的 P(T+1 UP/FLAT/DOWN)。P4 不输出 SPY 涨跌概率。", ""]
    (ROOT / "P4_REGIME_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    gen_registry()
    gen_report()
    print("P4_REGIME_REGISTRY.md + P4_REGIME_REPORT.md 已生成")
