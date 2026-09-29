# P7 STEP 6.5D — Production Availability Path Report

**STATUS: BLOCKED**（4 个 blocker 生产 runtime 仍 UNVERIFIABLE，vendor 未切换）
**L5 FINAL: BLOCKED**

---

## 1. 三层区分（用户第 15 节）

```
source capability           = 已证明（6.5C-1：SEC EDGAR filed/filingDate = PIT_SAFE 能力）
configured production path  = 已审计（default_config fundamental_data=yfinance）
actual runtime observation  = 待验证（sec.gov 网络阻断，无法真实 runtime 调用）
```

三层必须都成立才允许 tool = PIT_SAFE。当前第 2、3 层未成立 → 4 个 blocker 均 UNVERIFIABLE。

## 2. Production Path Matrix（4 个 blocker）

| tool | configured | actual runtime provider | candidate PIT-safe | runtime status |
| --- | --- | --- | --- | --- |
| get_balance_sheet | yfinance | `filter_financials_by_date`（period_end，无 filing date） | sec_edgar `_as_of` filed<=T | UNVERIFIABLE |
| get_cashflow | yfinance | `filter_financials_by_date`（period_end） | sec_edgar `_as_of` filed<=T | UNVERIFIABLE |
| get_income_statement | yfinance | `filter_financials_by_date`（period_end） | sec_edgar `_as_of` filed<=T | UNVERIFIABLE |
| get_insider_transactions | yfinance | `Start Date`（transaction date） | SEC EDGAR submissions filingDate（未接入） | UNVERIFIABLE |

## 3. SOURCE CAPABILITY

```
SEC EDGAR fundamentals（sec_edgar.py _as_of）:
    fact["filed"] > curr_date → 过滤（future filing rejection）
    filed <= curr_date → 保留，amendment 取最新 filed（revision vintage）
    → PIT_SAFE 能力（6.5C-1 验证）

SEC EDGAR insider（submissions filingDate）:
    → PIT_SAFE 能力（6.5C-1 真实 Form 4 验证）
    → 但 router 未绑定 sec_edgar 的 insider 实现
```

## 4. CONFIGURED PROVIDER / ACTUAL RUNTIME PROVIDER

```
default_config.py fundamental_data = "yfinance"
router VENDOR_METHODS:
    get_balance_sheet → yfinance（sec_edgar 已实现但默认未启用）
    get_insider_transactions → yfinance/alpha_vantage（sec_edgar 无绑定）
```

## 5. FALLBACK STATUS

```
无 silent fallback（router route_to_vendor 第 195-209 行）：
    配置的 vendor 列表就是 chain，不静默 fallback 到未配置 vendor
fail-closed sentinel：
    sec_edgar 失败 → VendorRateLimitError → DATA_UNAVAILABLE sentinel
    （明确"report unavailable, do not fabricate"）
非 US filer → cik_for None → NoMarketDataError（不 fallback yfinance）
```

## 6. AGENT TRACE（真实 insider runtime trace，非 Agent 声称）

用真实 Form 4 artifact（0001127602-24-019342）构建 runtime trace：

```
agent             = fundamentals_analyst
tool              = get_insider_transactions
vendor            = sec_edgar（candidate）
record_id         = 0001127602-24-019342
transaction_date  = 2024-06-26（form4.xml parser）
filing_date       = 2024-06-27（submission header parser）
available_at      = 2024-06-27（= filing_date，≠ transaction_date）
as_of             = 2024-06-27 23:59:59
```

**available_at ≠ transaction_date** 已由真实 source 证明。

## 7. TEST RESULTS

```
test_production_availability.py     6 passed（configured vendor / binding / filed 过滤 / vintage）
test_production_fallback.py         4 passed（typed error / fail-closed / no silent fallback）
test_production_mutation.py         4 passed（future filing / legitimate / revision / vintage）
test_production_runtime_trace.py    5 passed（trace 字段 / available_at / audit）
合计                                 19 passed
```

## 8. 最终状态

```
INSIDER:      UNVERIFIABLE（生产 yfinance，SEC Form 4 source 未接入 router）
FUNDAMENTALS: UNVERIFIABLE（生产 yfinance，SEC EDGAR filed 未启用）
L5:           BLOCKED（4 个 blocker 生产 runtime UNVERIFIABLE）
```

## 9. L5 聚合

```
for every reachable in-scope runtime tool:
    runtime_availability_status in {"PIT_SAFE"}  → 不满足（4 个 UNVERIFIABLE）

→ L5 = BLOCKED（用户第 14 节情况 C）
```

## 10. Regression

```
quant_engine   389 passed / 0 failed
TradingAgents  1001 passed + 91 subtests / 0 failed
P1-P7 / 6.4 / 6.5 / 6.5B / 6.5C / 6.5C-1：无回归失败
```

## 11. Modified / Added Files

```
新增 quant_engine/oos/production_availability_matrix.py（4 blocker 审计矩阵）
新增 quant_engine/tests/oos/test_production_availability.py（6 tests）
新增 quant_engine/tests/oos/test_production_fallback.py（4 tests）
新增 quant_engine/tests/oos/test_production_mutation.py（4 tests）
新增 quant_engine/tests/oos/test_production_runtime_trace.py（5 tests）
（TradingAgents / P1-P7 graph / default_config / router：零改动 —— 未切 vendor）
```

## 12. 诚实约束

- **未切换生产 vendor**（用户第 20 节"不要自动改生产配置"）。
- **sec.gov 网络阻断**：sec_edgar 无法真实 runtime 调用，runtime observation 依赖 6.5C-1 真实 artifact 验证（capability 层），production runtime 层（真实网络调用）仍 NOT_VERIFIED。
- 切 `fundamental_data=sec_edgar` + insider 接入 SEC Form 4 是**独立的 configuration remediation**（用户第 12 节：记录 old_vendor/new_vendor/config_version/effective_time/coverage），需在可访问 sec.gov 的环境执行。

STOP。不进入 STEP 6.6。
