# GOLDEN_DATASET.md — P1 回归基线（不可变）

> 状态：**GOLDEN_DATASET = PASS (13/13)**
> 生成：2026-09-27，`build_golden_dataset.py`
> 回归：`golden_regression.py`（只读，绝不修改 golden_dataset/）

## 用途

后续所有数据层/模型层/OpenD API 修改的 regression 地基。改完重跑 `golden_regression.py`，checksum / 行数 / PIT / schema 不变式必须全 PASS。

## 样本 + checksum（SHA-256，canonical JSON）

| 日期 | daily rows | daily checksum | 15m rows | 15m checksum |
|---|---|---|---|---|
| 2013-01-02 | 5 | `1caa130e…318c4a` | **UNAVAILABLE** | — |
| 2020-03-16 | 5 | `864c1e5d…7c9d76` | 130 | `41a73d39…a3da63` |
| 2024-01-02 | 5 | `79537a85…fdc220` | 130 | `87d82e2e…48a178` |
| 2026-09-23 | 5 | `49cbb0f0…a9d1c` | 130 | `a1e84864…1c6c54` |
| 2026-09-24 | 5 | `a7bc87d4…721cb` | 130 | `88f65f12…2e1fead` |
| 2026-09-25 | 5 | `452ddcd9…77f1d3` | 130 | `9d758deb…01b9d08` |

- option_chain_sample：350 行，checksum `d8f43bcc…3a228`，realtime=VERIFIED / historical=UNVERIFIED

## 每样本锁定内容

- raw（OpenD 原始 K线 CSV）、canonical（MarketDataPoint JSON）、validation、as_of replay
- PIT 四时间字段、price_basis=unadjusted、adjustment=NONE、session/timezone、source、schema/version

## 锁定的不变式（regression 校验）

1. price_basis = `unadjusted`（禁止复权转换）
2. adjustment = `NONE`
3. available_at >= observation_time（无未来数据）
4. 15m observation_time == timestamp（16:00 bar = 15:45–16:00，不得改回 start-time）
5. historical_pit_reconstruct = `UNVERIFIED`（不得标 VERIFIED）

## 已知边界

- **2013 的 15m 拉不到**（OpenD 历史日内数据边界约在 2013 之后某点；2020 起都有 15m）
- daily 全 6 日期可拉（2013 起）

## 目录

```
golden_dataset/
├── manifest.json        # 元数据 + checksums（immutable=true）
├── raw/                 # 原始 K线 CSV（daily/15m/期权样本）
├── canonical/           # MarketDataPoint JSON
├── validation/          # 校验结果
└── replay/              # as_of 可见性回放结果
```
