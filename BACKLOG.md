# Engineering Backlog / P1.x

P1 已 LOCK。以下为非阻塞技术债，**不重新打开 P1**，等真正需要时一次性处理。

| # | 项目 | 类型 | 说明 |
| --- | --- | --- | --- |
| 1 | CLI entrypoints | Tooling/DX | `python -m quant_engine.data ingest/query/validate/summary` |
| 2 | Macro symbol metadata registry | Data dictionary | ^FVX/^TNX/DXY/WTI 的 symbol/human_name/unit/scale/economic_meaning 完整表达 |
| 3 | Exact dual-as_of regression | PIT regression | 2024-06-01 12:00 vs 06-03 10:00 精确案例 |

## 备注

- 第 1、2 项已有纯新增实现（`quant_engine/data/__main__.py`、`quant_engine/data/macro_metadata.py`），
  作为 P1.x Tooling 的现成起点，**不修改 P1 核心**（models/pit/repository/calendar/validation 均未动）。
- 第 3 项：现有 PIT 验收已覆盖「收盘前不可见 / 收盘后可见 / future → NOT RETURNED」，
  仅缺旧任务书指定的具体日期组合，非 PIT 语义缺失。
