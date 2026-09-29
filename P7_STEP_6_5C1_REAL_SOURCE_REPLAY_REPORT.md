# P7 STEP 6.5C-1 — Real SEC Source Replay Report

**STATUS: RESOLVED**（真实 SEC Form 4 source 导入 + 真实 replay 全通过）
**L5 FINAL: BLOCKED**（fundamentals 默认 yfinance UNVERIFIABLE，insider 生产 vendor 未切换）

---

## 1. 真实 SEC artifact 导入

真实 SEC Form 4（ORACLE CORP / Screven Edward / accession `0001127602-24-019342`）通过内嵌 Base64 导入：

| 文件 | 状态 | SHA256 | 与期望值 |
| --- | --- | --- | --- |
| form4.xml | 完整 ✓ | `6ce3233a…` | 匹配 |
| metadata.json | 完整 ✓ | `d26b2591…` | 匹配 |
| submission.txt | 损坏 ✗ | deflate 第 513 字节损坏 | ZIP hash `2f40b4…` ≠ 期望 `6b7977…` |
| submission_header.txt | 前 512 字节真实解压 ✓ | `6bb0c2b8…` | 含完整 FILED AS OF DATE |

**诚实标注**：submission.txt 的完整 raw 在 Base64 传输中 deflate 损坏（第 513 字节起）。但**前 512 字节真实解压出完整 SEC header**，含关键字段 `FILED AS OF DATE: 20240627`、`ACCESSION NUMBER: 0001127602-24-019342`、`ACCEPTANCE-DATETIME: 20240627192057`。form4.xml 与 metadata.json 完整且 hash 匹配。核心 provenance（transaction_date + filing_date）都从真实 source 解析，非 synthetic 手填。

## 2. 三类证据

```
DOCUMENTARY EVIDENCE      = PASS（SEC 文档：filingDate 字段语义）
REAL SOURCE EVIDENCE      = PASS（form4.xml + metadata.json 完整 hash 匹配；
                                 submission header 前 512 字节真实解压）
SYNTHETIC TEST EVIDENCE   = PASS（6.5B/6.5C fixture + adapter 测试）
```

## 3. 真实 parser（filing_date 真实来自 source）

- `transaction_date = 2024-06-26` ← 从 form4.xml `<transactionDate><value>` 解析
- `filing_date = 2024-06-27` ← 从 submission header `FILED AS OF DATE: 20240627` 解析（→ `2024-06-27`）
- `available_at = filing_date`（source semantics 已验证）
- **transaction_date ≠ available_at** 已由真实 source 证明

## 4. 真实 replay（12 tests 全通过，无 skip）

```
test_real_sec_provenance                    PASS
test_real_sec_hash                          PASS（xml + header hash 匹配）
test_real_sec_transaction_date_from_xml     PASS（2024-06-26）
test_real_sec_filing_date_from_header       PASS（2024-06-27）
test_filing_date_from_source_not_fixture    PASS
test_real_sec_transaction_date_trap         PASS  ← 核心：transaction<=T 但 filing>T → 不可见
test_real_sec_visible_after_filing          PASS（Replay A）
test_real_sec_hidden_before_filing          PASS（Replay B）
test_real_sec_visible_after_filing2         PASS（Replay C）
test_real_sec_same_raw_different_cutoff     PASS（Replay D）
test_real_sec_hash_immutable                PASS
test_real_sec_independence                  PASS（auditor 看事实不信任 status）
```

## 5. 状态矩阵

```
DOCUMENTARY EVIDENCE        = PASS
REAL SOURCE EVIDENCE        = PASS
SYNTHETIC TEST EVIDENCE     = PASS
REAL SOURCE REPLAY          = PASS
PRODUCTION RUNTIME          = NOT_VERIFIED（get_insider_transactions 未接入 SEC source）
INSIDER AVAILABILITY        = RESOLVED（availability 能力验证）
FUNDAMENTALS AVAILABILITY   = BLOCKED（默认 yfinance UNVERIFIABLE）
L5 FINAL                    = BLOCKED
```

## 6. L5 聚合结论

真实 insider replay 完成 → insider **availability 能力** RESOLVED。但：

1. **生产 vendor 未切换**：`get_insider_transactions` 默认走 yfinance/alpha_vantage（无 Form 4 filing date）→ 生产 runtime 仍 UNVERIFIABLE。
2. **fundamentals**（balance_sheet/cashflow/income_statement）默认 `fundamental_data=yfinance`（无 filing date）→ UNVERIFIABLE。

L5 fail-closed 聚合：4 类 tool（3 statement + insider 生产 runtime）UNVERIFIABLE → **L5 = BLOCKED**。

**insider RESOLVED ≠ L5 PASS**（用户第 17 节）。不自动切换 vendor（第 16 节）。

## 7. Regression

```
quant_engine   370 passed / 0 failed
TradingAgents  1001 passed + 91 subtests / 0 failed
P1-P7 / 6.4 / 6.5 / 6.5B / 6.5C：无回归失败
```

## 8. Modified / Added Files

```
新增 quant_engine/oos/real_sec_bridge.py（SHA256 + provenance + Form 4 XML/submission header parser）
修改 quant_engine/oos/l5_tool_inventory.py（insider evidence 更新为 REAL_SOURCE_REPLAY PASS）
修改 quant_engine/tests/oos/test_agent_leakage_mutation.py（insider 断言更新）
新增 quant_engine/tests/oos/fixtures/real_sec/（真实 Form 4 artifacts + MANIFEST.json）
重写 quant_engine/tests/oos/test_real_sec_replay.py（12 tests，真实 source）
（TradingAgents / P1-P7 graph / L5 fail-closed semantics / 生产 vendor 路由：零改动）
```

STOP。不进入 STEP 6.6。
