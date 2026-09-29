# -*- coding: utf-8 -*-
"""生成 P3_EVENT_STUDY_REPORT.md + P3_LABEL_REPORT.md。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from quant_engine.events import run_event_study, EventRegistry
from quant_engine.labels import run_label_pipeline

ROOT = Path(r"F:\Youtube\0413\TradingAgents")


def gen_event_report():
    res = run_event_study(start="2013-01-01", end="2026-09-25")
    stats = res["statistics"].copy()
    gate = res["sample_size_gate"]
    stats["status"] = stats["event"].map(lambda e: gate.get(e, "SUFFICIENT"))

    lines = ["# P3_EVENT_STUDY_REPORT.md — Event Study 报告", ""]
    lines += ["## 概览", "",
              f"- 事件定义数：{len(EventRegistry.all())}",
              f"- 去重后事件总数：{res['event_count']}",
              f"- 唯一事件类型：{res['unique_events']}",
              f"- 样本不足（<30）：{sum(1 for v in gate.values() if v == 'INSUFFICIENT_SAMPLE')} 个事件", ""]

    lines += ["## Event × Horizon 条件分布", "",
              "| Event | Horizon | N | Mean | Median | Win Rate | Std | P25 | P75 | Status |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for _, r in stats.iterrows():
        lines.append(f"| {r['event']} | {r['horizon']} | {int(r['N'])} "
                     f"| {r['mean']:.4%} | {r['median']:.4%} | {r['win_rate']:.1%} "
                     f"| {r['std']:.4%} | {r['p25']:.4%} | {r['p75']:.4%} | {r['status']} |")
    lines.append("")
    (ROOT / "P3_EVENT_STUDY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def gen_label_report():
    out = run_label_pipeline(start="2013-01-01", end="2026-09-25")
    lines = ["# P3_LABEL_REPORT.md — Label Engine 报告", "",
             "threshold_method = realized_vol_daily；threshold = 0.5 × realized_vol_20 / sqrt(252)", ""]
    lines += ["| Horizon | 总数 | UP | FLAT | DOWN | 缺失（无未来 endpoint） |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for h in ("T+1", "T+2"):
        recs = out[h]
        c = Counter(l.label for l in recs)
        n = int(h.replace("T+", ""))
        missing = n  # 末尾 n 个交易日无未来 endpoint
        lines.append(f"| {h} | {len(recs)} | {c['UP']} | {c['FLAT']} | {c['DOWN']} | {missing} |")
    lines.append("")
    lines += ["## 分布说明", "",
              "- 分布为真实历史分布，未做任何阈值调整以让 UP/FLAT/DOWN 均衡。",
              "- missing = 数据末尾的 n 个交易日（无 T+n 未来 endpoint），不生成 label（非 FLAT）。", ""]
    (ROOT / "P3_LABEL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    gen_event_report()
    gen_label_report()
    print("P3_EVENT_STUDY_REPORT.md + P3_LABEL_REPORT.md 已生成")
