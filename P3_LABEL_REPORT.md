# P3_LABEL_REPORT.md — Label Engine 报告

threshold_method = realized_vol_daily；threshold = 0.5 × realized_vol_20 / sqrt(252)

| Horizon | 总数 | UP | FLAT | DOWN | 缺失（无未来 endpoint） |
| --- | ---: | ---: | ---: | ---: | ---: |
| T+1 | 3433 | 1147 | 1428 | 858 | 1 |
| T+2 | 3432 | 1473 | 970 | 989 | 2 |

## 分布说明

- 分布为真实历史分布，未做任何阈值调整以让 UP/FLAT/DOWN 均衡。
- missing = 数据末尾的 n 个交易日（无 T+n 未来 endpoint），不生成 label（非 FLAT）。
