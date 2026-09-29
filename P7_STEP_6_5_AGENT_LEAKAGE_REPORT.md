# P7 STEP 6.5 — Agent Research Runtime OOS Leakage Audit（L5）

**STATUS: BLOCKED**（撤回此前 PASS，fail-closed）

---

## 1. L5 Contract（fail-closed）

对每一条 Agent-observed record：
```
SAFE        iff available_at <= T（或正式 vendor guarantee 证明 T 前公开可用）
UNSAFE      iff available_at > T 或 publication/filing/revision > T
UNVERIFIABLE iff available_at 无法建立
```
```
L5 PASS    only if 所有 in-scope 外部数据路径都 SAFE
L5 BLOCKED if 任一 reachable in-scope tool 是 UNVERIFIABLE
L5 FAIL    if 证明未来信息进入 Agent observation
```
`UNVERIFIABLE ≠ SAFE`，`UNVERIFIABLE ≠ "非泄漏"`。
`period_end <= T` / `transaction_date <= T` **不能**证明 `available_at <= T`。

## 2. 四类 tool 的 historical availability 语义（沿 vendor/source 层追到底）

| Tool | 默认 vendor | 有 filing/availability date? | availability 语义 |
| --- | --- | --- | --- |
| get_balance_sheet | yfinance（`fundamental_data=yfinance`） | ❌ 只有 period_end | UNVERIFIABLE |
| get_cashflow | yfinance | ❌ 只有 period_end | UNVERIFIABLE |
| get_income_statement | yfinance | ❌ 只有 period_end | UNVERIFIABLE |
| get_insider_transactions | yfinance / alpha_vantage | ❌ 只有 transaction_date（无 Form 4 filing date） | UNVERIFIABLE |

**关键发现（追到 raw source 层）**：

1. **yfinance**：`balance_sheet`/`income_stmt`/`cashflow` 的 columns 是 **fiscal period end dates**，无 filing date。
   `filter_financials_by_date` 按 `period_end <= curr_date` 切（fundamentals.py），
   `alpha_vantage` 按 `fiscalDateEnding <= curr_date` 切（fundamentals.py）。
   → 一个 `period_end=2024-05-31 <= T=2024-06-03` 的季度，若实际 filing 在 `2024-06-10`（> T），
   当前过滤会**错误保留**这条本应不可见的记录。

2. **SEC EDGAR**：`companyfacts` API 的每个 fact 带 **`filed` 字段（真实 filing date）**，
   `_as_of()` 用 `fact["filed"] > curr_date` 过滤（sec_edgar.py:167）——这是真正的 PIT_SAFE
   （`available_at = filing date`）。**但默认配置 `fundamental_data=yfinance`，EDGAR 未启用**，
   且 EDGAR 仅覆盖 US filers（非 US filer 回落到 yfinance）。

3. **insider transactions**：yfinance/alpha_vantage 都只提供 transaction date，**无任何 vendor 提供
   Form 4 filing date**。`transaction_date=2024-06-01 <= T=2024-06-03` 但 `filing_date=2024-06-05 > T`
   的内幕交易记录，当前过滤按 transaction date 切，会**错误保留**。

→ 四类 tool 在默认 runtime 下 **available_at 无法建立** → `UNVERIFIABLE_AVAILABILITY`。

## 3. Tool Inventory（12 tools，fail-closed 分类）

| Tool | 状态 | availability 字段 |
| --- | --- | --- |
| get_stock_data | PIT_SAFE | Date <= curr_date（真实 observation） |
| get_indicators | PIT_SAFE | Date <= curr_date |
| get_verified_market_snapshot | PIT_SAFE | Date <= curr_date |
| get_fundamentals | PIT_SAFE | withhold_live_profile（live-only 历史 withhold） |
| **get_balance_sheet** | **UNVERIFIABLE** | None（默认 yfinance）；filed 仅 sec_edgar 未启用 |
| **get_cashflow** | **UNVERIFIABLE** | 同上 |
| **get_income_statement** | **UNVERIFIABLE** | 同上 |
| get_news | PIT_SAFE | pub_date |
| get_global_news | PIT_SAFE | pub_date |
| **get_insider_transactions** | **UNVERIFIABLE** | None（无 Form 4 filing date） |
| get_macro_indicators | PIT_SAFE | FRED realtime vintage pin（防 revision） |
| get_prediction_markets | PIT_SAFE | 历史 withhold（无 live vintage） |

**8 PIT_SAFE + 4 UNVERIFIABLE，0 CURRENT_ONLY，0 LEAKAGE_RISK。**

## 4. Filtering correctness ≠ Historical availability proof

现有 mutation tests 证明的是"过滤规则正确"（future canary 被当前规则挡住），
**不能**自动证明"真实 vendor fundamentals 本身具有 historical availability semantics"。
二者是不同的事，报告区分：
- **Filtering correctness**：price/news/fundamental-period/revision canary 被挡 → PASS
- **Historical availability proof**：yfinance fundamentals/insider 无 filing date → UNVERIFIABLE

## 5. 关键 mutation：period_end ≠ availability

```
T = 2024-06-03
record: period_end = 2024-05-31, filing_date = 2024-06-10, available_at = 2024-06-10
预期：MUST NOT enter Agent observation
实际：yfinance schema 无法表达 filing_date → 无法过滤 → UNVERIFIABLE
```
`filter_financials_by_date` 只按 period_end 切，`2024-05-31 <= T` 被保留，
但 `filing_date=2024-06-10 > T` 无法被识别 → 这条记录本应不可见却被保留。

## 6. L5-A～M（tests PASS where applicable，overall BLOCKED）

```
L5-A  Tool inventory                  PASS（12 tool 全清单）
L5-B  Historical cutoff propagation   PASS（trade_date → as_of 钳制）
L5-C  News publication cutoff         PASS（pub_date <= T）
L5-D  Market-data cutoff              PASS（Date <= T）
L5-E  Fundamental availability        UNVERIFIABLE（yfinance 无 filing date）
L5-F  Sentiment/social cutoff         PASS（StockTwits created_at）
L5-G  Cache isolation                 PASS
L5-H  Revision isolation              PASS（FRED vintage pin）
L5-I  Future-canary isolation         PASS（filtering correctness）
L5-J  Audit independence              PASS（不依赖 agent 声称）
L5-K  Fail-closed behavior            PASS（UNVERIFIABLE → BLOCKED，不降级 PASS）
L5-L  Agent output attribution        PASS（tool trace + cutoff 证据）
L5-M  Two-anchor replay               PASS（2020-03-16 / 2024-06-03 trade_date 传播）
```

## 7. Regression

```
quant_engine   318 passed / 0 failed   （291 既有 + 27 L5）
TradingAgents  1001 passed + 91 subtests, 5 skipped / 0 failed
P1-P6 / P7 / STEP 6.4 regression：无失败
```

## 8. 最终结论

```
STATUS: BLOCKED
Proven Leakage: none observed
Unverifiable: 4 tool classes（get_balance_sheet / get_cashflow / get_income_statement / get_insider_transactions）
Overall L5: BLOCKED
```

**"Proven Leakage: none" ≠ "L5 PASS"。** 这 4 类 tool 的 historical availability
无法证明（默认 yfinance 只提供 period_end/transaction_date，无 filing date），
按 fail-closed contract 必须 BLOCKED，不允许猜测、不允许降级为 PASS。

**唯一的 PIT_SAFE 路径**：把 `fundamental_data` 切到 `sec_edgar`（EDGAR 提供 `filed` date），
但 insider transactions 仍无 vendor 提供 Form 4 filing date → 即使切 EDGAR，insider 仍 UNVERIFIABLE。
这是 contract gap，非本阶段可修（不修改 frozen P1-P6 / P7 / 不新增 vendor）。

## 9. Modified Files（REWORK）

```
改 quant_engine/oos/l5_models.py          ToolInventoryEntry 加 availability/filing/publication/revision 字段 + historical_availability_proven；AgentLeakageAuditResult 加 blocked_tools
改 quant_engine/oos/l5_tool_inventory.py  四类 tool 从 HISTORICAL_BUT_UNVERIFIED 改为 UNVERIFIABLE（补 availability 语义字段）
改 quant_engine/oos/l5_audit.py           fail-closed 聚合：UNSAFE→FAIL / UNVERIFIABLE→BLOCKED / 全 PIT_SAFE→PASS
改 tests/oos/test_agent_leakage_audit.py     PASS→BLOCKED 断言 + blocked_tools 断言
改 tests/oos/test_agent_leakage_mutation.py  增 period_end≠availability + transaction_date≠filing_date 测试
改 tests/oos/test_agent_leakage_independence.py  PASS→BLOCKED + 8/4 分类修正
（TradingAgents / P1-P7 / STEP 6.4 零改动）
```

STOP。不进入 STEP 6.6。
