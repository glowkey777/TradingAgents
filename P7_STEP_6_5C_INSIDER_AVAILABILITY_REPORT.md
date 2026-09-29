# P7 STEP 6.5C — Insider Historical Availability Remediation

**STATUS: BLOCKED**（撤回上次 RESOLVED，见 §0 更正说明）

---

## 0. 更正说明

上次（11-11-52 轮）报告 RESOLVED 是**错误的**。错误根源：把「fixture 基于官方文档字段结构构造」
当成了「真实 source replay」。用户第 10 节明确要求**真实 raw source response**，第 17 节 RESOLVED
硬条件含「historical replay verified」。本环境 sec.gov 的 TLS 握手被网络层阻断（Schannel、OpenSSL
via requests、httpx 全部 SSL EOF；直连、http 代理、socks 代理全部失败），**无法获取真实 SEC raw
response**，因此「historical replay verified」不满足 → 不能 RESOLVED。

## 1. 当前 source inventory

现有代码 + 配置无任何 vendor 提供 insider Form 4 filing date（全库搜索确认）：

| vendor | insider 字段 | filing date |
| --- | --- | --- |
| yfinance | `Start Date`（transaction date） | ❌ 无 |
| alpha_vantage | `transaction_date` | ❌ 无 |

## 2. Candidate source capability

| source | endpoint | filing_date_field | status |
| --- | --- | --- | --- |
| SEC EDGAR submissions | `data.sec.gov/submissions/CIK{cik}.json` | `filingDate` | PIT_SAFE（文档级） |
| yfinance insider | Ticker.insider_transactions | 无 | UNVERIFIABLE |
| alpha_vantage insider | INSIDER_TRANSACTIONS | 无 | UNVERIFIABLE |

SEC EDGAR submissions 字段语义（sec-edgar-api.readthedocs.io + SEC 官方文档）：
`filings.recent` 是 columnar array，`form`/`filingDate`/`accessionNumber`/`acceptanceDateTime` 同索引对齐，
`filingDate` = Form 4 提交日，无 key。

## 3. Filing-date semantics（文档级已验证）

`filingDate` = Form 4 提交到 SEC 的日期 = 公开可获得时间。`filingDate <= T` → `available_at <= T`。
amendment（4/A）按自己 filingDate 计，revision isolation 天然成立。

**但这是文档级验证，不是 runtime 验证**（见 §4）。

## 4. Historical replay capability（⚠ 未完成）

- **真实 API replay：未完成**。本环境 sec.gov TLS 握手被阻断，尝试了：
  - curl 直连 / `--insecure` / `--http1.1` / 走 http 代理 → Schannel SSL handshake 失败
  - Python requests 直连 / 走代理 → SSLError EOF
  - httpx 直连 / 走代理 → ConnectError SSL EOF
  - socks5 10809 → 连接被拒
  - web_extract → SSRF 阻止
  → **无法获取真实 raw source response**，真实 replay 无法验证。
- fixture 是基于官方文档字段结构构造的（非真实 raw response），已在 `_retrieval_metadata` 如实标注。

## 5. Adapter（已实现，逻辑正确但未经真实数据验证）

```
quant_engine/oos/insider_source_matrix.py
quant_engine/oos/insider_availability_adapter.py
    sec_edgar_insider_filing_availability(filing, as_of) -> AvailabilityEvidence
    sec_edgar_insider_form4_rows(filings_recent) -> [Form 4 rows]
```
复用 6.5B 的 `HistoricalAvailabilityProvider` + `AvailabilityEvidence`。fail-closed：
```
filingDate None → UNVERIFIABLE；filingDate > T → VIOLATION；否则 PROVEN
transaction_date 不进入 PROVEN 判断
```

## 6. Mutation tests（11 passed，fixture-based）

4 核心（future filing / legitimate / transaction 不能替代 / future revision）+ fixture replay +
snapshot trap + cache isolation + negative control + independence ×2 全过。
**但这些是 synthetic/fixture 验证，不是真实 source 验证。**

## 7. Cache isolation / 8. Independent audit

- cache：filingDate 是 record-level，`filingDate <= T` 过滤在 cache 后仍应用（test 验证）。
- audit：复用 6.5B `audit_availability`，优先看 available_at 事实，不信任 status 声称。

## 9. Runtime integration

未接入（本阶段不改 Agent graph）。`fundamentals_analyst` 仍走 yfinance/alpha_vantage（UNVERIFIABLE）。

## 10. Regression

```
quant_engine   358 passed / 0 failed   （347 既有 + 11 新增 6.5C）
TradingAgents  1001 passed + 91 subtests / 0 failed
P1-P7 / 6.4 / 6.5 / 6.5B：无失败
```

## 11. STEP 6.5C = BLOCKED

```
source verified          ✓  文档级（SEC EDGAR submissions filingDate）
filing semantics         ✓  文档级
adapter                  ✓  已实现（fail-closed）
mutation tests           ✓  11 passed（fixture-based）
cache isolated           ✓
independent audit        ✓
historical replay        ✗  环境 sec.gov TLS 阻断，无法获取真实 raw response
Agent runtime trace      ✗  未接入
```

RESOLVED 硬条件「historical replay verified」不满足（环境网络阻断，非 fixture 可替代），
按 fail-closed 原则 → **BLOCKED**。不 mock、不 infer、不 substitute、不 relax contract。

**BLOCKER**：
```
No reachable insider source provides auditable historical
Form 4 filing/availability evidence.
SEC EDGAR submissions 提供 filingDate（文档确认），但本环境
sec.gov TLS 阻断 → 不可达 → 无法真实 replay 验证。
```

## 12. L5 aggregate impact

STEP 6.5C = BLOCKED → **L5 = BLOCKED**（insider 仍 UNVERIFIABLE）。

```
STATUS: BLOCKED
Proven Leakage: none observed
Unverifiable: insider（无 reachable Form 4 filing date source）+ statement（默认 yfinance 无 filing date）
Overall L5: BLOCKED
```

## 13. Modified Files

```
新增 quant_engine/oos/insider_source_matrix.py
新增 quant_engine/oos/insider_availability_adapter.py
新增 tests/oos/fixtures/insider/sec_edgar_submissions_aapl.json（构造 fixture，标注来源）
新增 tests/oos/test_insider_availability.py（11 tests）
（TradingAgents / P1-P7 / 6.4 / 6.5 / 6.5B 零改动）
```

## 14. 若要 RESOLVED 的前置条件

需在**可访问 sec.gov 的网络环境**（或接入可信的 SEC 数据 mirror）：
1. 获取真实 SEC EDGAR submissions raw response 存入 fixture
2. 用真实数据跑 replay test（filingDate <= T 过滤）
3. 验证真实 Form 4 XML 解析链路（transaction 详情）
4. 然后重新判定 STEP 6.5C，并 re-run L5 aggregate

STOP。不进入 STEP 6.6。
