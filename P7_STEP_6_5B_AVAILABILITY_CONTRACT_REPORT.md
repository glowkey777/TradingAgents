# P7 STEP 6.5B — Historical Availability Contract Gap Resolution

**STATUS: BLOCKED**（合法结果：insider 无可靠 filing date source，不强行找 vendor 降级 PASS）

---

## 1. Source Capability Matrix

| source | vendor | tool | availability_field | status |
| --- | --- | --- | --- | --- |
| Yahoo Finance | yfinance | get_balance_sheet | ❌（仅 period_end） | UNVERIFIABLE |
| Yahoo Finance | yfinance | get_cashflow | ❌（仅 period_end） | UNVERIFIABLE |
| Yahoo Finance | yfinance | get_income_statement | ❌（仅 period_end） | UNVERIFIABLE |
| Alpha Vantage | alpha_vantage | get_balance_sheet | ❌（仅 fiscalDateEnding） | UNVERIFIABLE |
| Alpha Vantage | alpha_vantage | get_cashflow | ❌（仅 fiscalDateEnding） | UNVERIFIABLE |
| Alpha Vantage | alpha_vantage | get_income_statement | ❌（仅 fiscalDateEnding） | UNVERIFIABLE |
| **SEC EDGAR** | sec_edgar | get_balance_sheet | ✅ **filed** | **PIT_SAFE** |
| **SEC EDGAR** | sec_edgar | get_cashflow | ✅ **filed** | **PIT_SAFE** |
| **SEC EDGAR** | sec_edgar | get_income_statement | ✅ **filed** | **PIT_SAFE** |
| Yahoo Finance | yfinance | get_insider_transactions | ❌（仅 Start Date） | UNVERIFIABLE |
| Alpha Vantage | alpha_vantage | get_insider_transactions | ❌（仅 transaction_date） | UNVERIFIABLE |
| FRED | fred | get_macro_indicators | ✅ realtime vintage | PIT_SAFE |
| Yahoo news | yfinance | get_news | ✅ pub_date | PIT_SAFE |
| StockTwits | stocktwits | social | ✅ created_at | PIT_SAFE |
| Polymarket | polymarket | prediction_markets | ✅ withhold | PIT_SAFE |

## 2. yfinance evidence

`balance_sheet`/`income_stmt`/`cashflow` 的 columns 是 **fiscal period end dates**，无 filing date。
`filter_financials_by_date` 按 `period_end <= curr_date` 切。代码已诚实标记 `_PERIOD_END_VINTAGE`
（"this vendor does not report filing dates"）。
→ `period_end <= T` 不能证明 `available_at <= T` → **UNVERIFIABLE**。

## 3. alpha_vantage evidence

`_filter_reports_by_date` 按 `fiscalDateEnding <= curr_date` 切，无 filing date。
→ **UNVERIFIABLE**（同 yfinance）。

## 4. SEC EDGAR evidence（SEC_EDGAR_COMPANYFACTS_V1）

`companyfacts` API 每个 fact 带 `filed` 字段，经 XBRL Guide 验证：
- `filed` = filing date（提交到 EDGAR 的日期，提交即公开）
- `form` = 10-K / 10-Q / 8-K ...
- `end` / `start` = reporting period；`val` = value

`_as_of()` 用 `fact["filed"] > curr_date` 过滤，restatement 按 amendment 的 filing 计。
**`filed <= T` 严格证明 `available_at <= T` → PIT_SAFE（verified）。**

**但两个限制**：
1. 默认配置 `fundamental_data=yfinance`，EDGAR **未启用**（当前 runtime 走 yfinance）。
2. EDGAR 仅覆盖 US SEC filers（非 US filer 回落到 yfinance）。

## 5. insider vendor evidence

| vendor | 字段 | filing date |
| --- | --- | --- |
| yfinance | `Start Date`（transaction date） | ❌ 无 |
| alpha_vantage | `transaction_date` | ❌ 无 |

两者都**无 Form 4 filing date**。代码已诚实标记 `_TRANSACTION_DATE_VINTAGE`
（"a trade becomes public when its Form 4 is filed, up to two business days later"）。
`transaction_date <= T` 不能证明 `filing_date <= T` → **UNVERIFIABLE**。

## 6. AvailabilityEvidence Contract

```
AvailabilityEvidence（frozen=True，deterministic 序列化）
    status: PROVEN / UNVERIFIABLE / VIOLATION
    available_at: datetime | None   ← 与 period_end 语义完全独立
    source / source_field / record_id / as_of / reason
```
`period_end` 描述"数据代表哪个经济期间"，`available_at` 描述"T 时是否公开可见"，**永远独立**。

## 7. Availability Auditor（独立）

```
audit_availability(evidence)：
    优先看 available_at 事实字段，不信任 status 声称
    available_at <= as_of  → SAFE（即使 source 声称 UNVERIFIABLE）
    available_at >  as_of  → VIOLATION→UNSAFE；PROVEN 声称→FAIL（source 撒谎）
    available_at 是 None   → VIOLATION→UNSAFE / UNVERIFIABLE→BLOCKED / PROVEN→BLOCKED（矛盾）
```

## 8. Mutation results（4 组全过）

```
Mutation A  period_end<=T + filing>T    yfinance→UNVERIFIABLE；EDGAR filed>T→VIOLATION   ✓
Mutation B  period_end<=T + filing<=T   EDGAR filed<=T→PROVEN/SAFE                       ✓
Mutation C  filing<=T + revision>T      原始保留，修订 fact filed>T→VIOLATION（隔离）      ✓
Mutation D  transaction<=T + filing>T   有 filing_date→VIOLATION；无→UNVERIFIABLE         ✓
```

## 9. Independence results（4 组全过）

```
source 声称 PROVEN 但 available_at>T      → FAIL   ✓
source 声称 UNVERIFIABLE 但 available_at<=T → SAFE（audit 识别事实）✓
auditor 不依赖 status 字符串               → 一致结果 ✓
声称 PROVEN 却无 available_at              → BLOCKED（矛盾）✓
```

## 10. Reachable / unreachable tool status

`fundamentals_analyst.py` 显式绑定 4 个 tool（imports + tool list + prompt）：
```
get_balance_sheet / get_cashflow / get_income_statement / get_insider_transactions
```
→ **4 个 tool 全部 reachable + in-scope**，不能排除出 L5 gate（有 graph/tool binding 证据）。

## 11. Impact on L5

fail-closed 聚合（用户第 15 节）：
```
FAIL    if 任一 PROVEN VIOLATION
BLOCKED if 任一 reachable in-scope tool UNVERIFIABLE
PASS    else
```

- SEC EDGAR 对 3 个 statement 可 PIT_SAFE，但**默认未启用**，且**不覆盖 insider**。
- insider 两个 vendor 都 UNVERIFIABLE，且 reachable + in-scope。

→ **SEC EDGAR PASS 不能覆盖 insider UNVERIFIABLE → L5 = BLOCKED。**

```
STATUS: BLOCKED
Proven Leakage: none observed
Unverifiable: insider（无 Form 4 filing date source）+ statement（默认 yfinance 无 filing date）
Overall L5: BLOCKED
```

## 12. Regression

```
quant_engine   347 passed / 0 failed   （318 既有 + 29 新增 6.5B）
TradingAgents  1001 passed + 91 subtests, 5 skipped / 0 failed
P1-P6 / P7 / STEP 6.4 / STEP 6.5 regression：无失败
```

## 13. Modified Files

```
新增 quant_engine/oos/availability_models.py       AvailabilityEvidence / SourceCapability / 状态枚举
新增 quant_engine/oos/availability_source_matrix.py  Source Capability Matrix（15 行）
新增 quant_engine/oos/availability_audit.py        AvailabilityAuditor（独立，看 available_at 事实）
新增 quant_engine/oos/availability_adapters.py     HistoricalAvailabilityProvider + 4 个 adapter
新增 tests/oos/test_availability_contract.py       6 测试
新增 tests/oos/test_availability_sources.py        9 测试
新增 tests/oos/test_availability_mutation.py       8 测试
新增 tests/oos/test_availability_independence.py   4 测试
新增 tests/oos/test_availability_l5_gate.py        3 测试
（TradingAgents / P1-P7 / STEP 6.4 / STEP 6.5 零改动；默认 vendor 配置未改）
```

## 14. 最终结论

**STEP 6.5B = BLOCKED，L5 = BLOCKED。**

insider filing date 当前没有可靠 source：yfinance 与 alpha_vantage 都只提供 transaction date，
无 Form 4 filing date。按 fail-closed contract，不 mock、不 infer、不 substitute transaction_date，
最终保持 BLOCKED。

**若要 RESOLVED**：需要接入一个提供 Form 4 filing date 的 insider source（例如 SEC EDGAR
ownership/submissions 数据，或 Finnhub insider-transactions API 的 `filing_date` 字段），
并将 `fundamental_data` 切到 `sec_edgar`——这两步都属于新 vendor/新配置，超出本阶段
"不改 frozen P1-P7、不新增 vendor" 的边界，留待后续 remediation 子步骤。

STOP。不进入 STEP 6.6。
