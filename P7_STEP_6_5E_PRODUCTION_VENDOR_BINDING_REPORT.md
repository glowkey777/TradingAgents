# P7 STEP 6.5E — PRODUCTION VENDOR BINDING REMEDIATION REPORT

**日期**：2026-09-28
**状态**：STEP 6.5E = **COMPLETE**（4 个 blocker 全部绑定 PIT-safe provider，offline production replay PASS）
**L5 FINAL** = **BLOCKED**（online runtime 仍 NOT_VERIFIED，情况 A）

---

## 最终状态（第 22 节 情况 A）

```text
SOURCE_CAPABILITY           PASS        （6.5C-1 已验证 SEC EDGAR filed / Form 4 filingDate = PIT_SAFE）
OFFLINE_PRODUCTION_REPLAY   PASS        （本阶段：router → SEC adapter → 真实 Form 4 artifact）
ONLINE_PRODUCTION_RUNTIME   NOT_VERIFIED（sec.gov 网络层阻断，本环境无法真实 runtime 调用）
L5                          BLOCKED     （情况 A：不得把 offline replay 冒充 online runtime）
```

**没有自行宣布 L5 PASS。** 按 STEP 6.5 纪律：UNVERIFIABLE（online）→ 不默认 SAFE → fail-closed BLOCKED。

---

## 一、Binding Matrix（第 3 节）

`quant_engine/oos/production_vendor_binding_matrix.py`（104 行）

| tool | old_vendor | new_vendor | availability_field | status |
| --- | --- | --- | --- | --- |
| get_balance_sheet | yfinance | sec_edgar | filed | PIT_SAFE |
| get_cashflow | yfinance | sec_edgar | filed | PIT_SAFE |
| get_income_statement | yfinance | sec_edgar | filed | PIT_SAFE |
| get_insider_transactions | yfinance / alpha_vantage | sec_form4 | FILED AS OF DATE | PIT_SAFE |

`binding_summary()`：`all_bound=True`，`online_runtime=NOT_VERIFIED`。

---

## 二、实际绑定（第 4/6 节）

### Fundamentals（3 个 statement）
- **不改** `get_fundamentals`（profile 类，无 SEC EDGAR profile 实现，走 yfinance + withhold_live_profile）。
- 3 个 statement 用 `tool_vendors` 覆盖 → `sec_edgar`（复用已实现的 `_as_of`：`fact["filed"] > curr_date → filtered`）。

### Insider
- 新增 `tradingagents/dataflows/vendors/sec_form4.py`（90 行）：真实 Form 4 parser（transaction_date 从 form4.xml，filing_date 从 submission header），`filing_date > curr_date → 过滤`。
- router 绑定：`VENDOR_METHODS["get_insider_transactions"]["sec_form4"]` + `VENDOR_LIST` 加入 `sec_form4`。

### 配置版本化（第 8 节）
`default_config.py` 新增 `vendor_config_version`（`6.5E-v1`）：
```python
"vendor_config_version": {
    "statement_vendors":   {"old": "yfinance", "new": "sec_edgar"},
    "insider_transactions":{"old": "yfinance/alpha_vantage", "new": "sec_form4"},
    "coverage": "US SEC filers only",
    "unsupported_symbols": "non-US filer -> NoMarketDataError (no fallback)",
    "failure_behavior": "typed VendorRateLimitError -> DATA_UNAVAILABLE (no silent fallback)",
    "fallback_behavior": "no silent fallback; PIT safety > data completeness",
}
```

---

## 三、无 silent fallback（第 5/13/16 节）

- SEC 网络失败 → `VendorRateLimitError`（typed）→ `DATA_UNAVAILABLE`。
- 非 US filer → `NoMarketDataError`（fail-closed），不 fallback yfinance。
- `as_of` 早于 filing_date → 记录不可见，不返回当前 snapshot（`no current snapshot fallback`）。

---

## 四、配置历史 PIT（第 9 节）

`CONFIGURATION_CURRENT` 与 `HISTORICAL_PREDICTION_PROVENANCE` 分离。今天的 vendor 切换**不**追溯重写 2024 历史预测的 provenance。`vendor_config_version` 明确记录 `old`，无 `historical_prediction_rewrite` 字段。

---

## 五、测试（第 19 节，12 项覆盖）

新增 5 个测试文件 + 更新 3 个既有测试：

| 文件 | 覆盖 |
| --- | --- |
| `test_vendor_binding.py`（7） | configured vendor、router binding、binding matrix、summary |
| `test_production_sec_router.py`（4） | SEC fundamentals filed PIT、insider filing_date PIT、transaction≠available_at |
| `test_production_no_fallback.py`（5） | 无 silent fallback、无 current snapshot、unsupported filer fail-closed |
| `test_production_offline_replay.py`（3） | router-path offline replay（T=06-26 absent / T=06-27 present / dates from source） |
| `test_vendor_config_provenance.py`（5） | vendor_config_version、coverage/failure 记录、历史 provenance 不重写 |

**关键：offline replay 走完整 production path**（`route_to_vendor → sec_form4.get_insider_transactions → 真实 Form 4 artifact`），不是直接调 adapter（第 10 节）。

### 既有测试更新（回归修复）
- `test_dataflows_config.py`：默认 get_balance_sheet vendor 断言 `["yfinance"]` → `["sec_edgar"]`（tool_vendors 新默认）。
- `test_undated_tools_as_of.py`：monkeypatch 目标 yfinance → sec_edgar（get_balance_sheet 现在走 sec_edgar）。

---

## 六、Regression（第 20 节）

```text
quant_engine    413 passed / 0 failed
TradingAgents   1001 passed + 91 subtests / 0 failed
```

0 regression failures。

---

## 七、L5 impact（第 18/22 节）

```text
SEC fundamentals capability   PASS
SEC insider capability        PASS
configured vendor             sec_edgar / sec_form4（tool_vendors + vendor_config_version）
actual router vendor          sec_edgar / sec_form4（VENDOR_METHODS 已绑定）
offline production replay     PASS（真实 Form 4 artifact，router path）
online runtime verification   NOT_VERIFIED（sec.gov 网络阻断）
fallback behavior             fail-closed，无 silent fallback
coverage                      US SEC filers only
unsupported symbols           non-US filer -> NoMarketDataError
configuration version         6.5E-v1

L5 FINAL = BLOCKED（情况 A：online runtime 无 evidence，不得自行 PASS）
```

---

## 八、诚实约束（第 17/23 节）

- **ONLINE_PRODUCTION_RUNTIME = NOT_VERIFIED**，绝对未写 PASS。
- 未进入 STEP 6.6；未做模型性能/回测；未改 P5/P6/Agent graph。
- 未因为 source capability PASS 自动修改历史 provenance。

**STOP。** 唯一残留缺口：真实 sec.gov 网络可达环境下的 online runtime verification（`ONLINE_PRODUCTION_RUNTIME`），属环境依赖，非本阶段可解。
