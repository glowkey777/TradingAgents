# P7 STEP 6.5F — ONLINE PRODUCTION RUNTIME VERIFICATION REPORT

**日期**：2026-09-28
**状态**：STEP 6.5F = **BLOCKED**（合法结果，第 16 节）
**L5 FINAL** = **BLOCKED**

---

## 最终状态（第 15/16 节，严格分层）

```text
OFFLINE_REAL_SOURCE_REPLAY    PASS          （6.5C-1：真实 Form 4 12 tests + 6.5E：router-path offline replay）
ONLINE_SOURCE_REACHABILITY    BLOCKED       （本机 sec.gov 网络层阻断，DNS 劫持 + TLS 干扰）
ONLINE_PRODUCTION_RUNTIME     NOT_VERIFIED  （无法获得真实在线 response）
L5                            BLOCKED       （第 18 节规则：online_production_runtime_not_verified → BLOCKED）
```

**未 mock，未用 offline 冒充 online。** 按第 16 节纪律，环境阻断是合法结果，直接 BLOCKED。

---

## 一、Online Source Probe（第 5 节）—— 充分探测证据链

### 1. 最小 probe（production 同款 requests client）

| 目标 | 直连 | 代理 10808 |
| --- | --- | --- |
| data.sec.gov | ❌ SSLEOFError | ❌ SSLEOFError |
| www.sec.gov | ❌ SSLEOFError | ❌ SSLEOFError |

### 2. 代理连通性对照（排除「代理本身故障」）

| 目标 | 代理 10808 |
| --- | --- |
| google.com | ✅ HTTP 200（85536 B，代理工作正常） |
| cloudflare.com | ✅ HTTP 200 |
| finance.yahoo.com | ⚠️ HTTP 429（可连通，被限流） |
| **sec.gov** | ❌ **HTTP 000（唯独 sec.gov 连不上）** |

### 3. DNS 劫持（新发现，根因之一）

```text
nslookup data.sec.gov → 127.128.4.68 + fd00:696e:6974:6578::28:445
nslookup www.sec.gov  → 127.128.4.70 + fd00:696e:6974:6578::28:447
nslookup google.com   → 127.128.5.27 + fd00:...:28:51c   （google 也被劫持，但代理走 xray DNS 解析所以能通）
```

- 无论用系统 DNS、`8.8.8.8` 还是 `1.1.1.1`，sec.gov 都解析到 **`127.x.x.x` 回环地址**（每次变 IP）。
- `fd00:696e:6974:6578` hex 解码 = **"initex"**，是某个 DNS 劫持组件的标识（ULA 地址段）。

### 4. DoH 绕过 DNS 劫持查正确 IP

```text
data.sec.gov → 23.51.131.126（Akamai edgekey）
www.sec.gov  → 23.42.118.87（Akamai edgekey）
```

### 5. 绕过 DNS 劫持（正确 IP + 正确 SNI）仍失败 → TLS 层干扰

```text
直连 --resolve data.sec.gov:443:23.51.131.126  → schannel: failed to receive handshake
代理 + --resolve 正确 IP                        → HTTP 000
```

**结论**：即使拿到正确 IP 并用正确 SNI，TLS 握手仍被切断。这是**两层阻断**：① DNS 劫持（127.x + "initex" ULA）② TLS 干扰（Akamai 握手被切）。

---

## 二、逐项判定（第 20 节）

| 项 | 状态 | 依据 |
| --- | --- | --- |
| SEC reachability | **BLOCKED** | DNS 劫持 + TLS 干扰，直连/代理/绕 DNS 全失败 |
| Fundamentals online runtime | **NOT_VERIFIED** | sec_edgar 需真实 online response，无法获得 |
| Insider online runtime | **NOT_VERIFIED** | sec_form4 需真实 online response，无法获得 |
| Actual router vendor | 已绑定（6.5E） | `VENDOR_METHODS` 含 sec_edgar/sec_form4，但无法 online 验证 actual call |
| PIT cutoff | offline 已验证 | 6.5C-1 transaction-date trap；online 无法验证 |
| Future-data rejection | offline 已验证 | 6.5E offline replay（T_before absent / T_after present）；online 无法验证 |
| No fallback | offline 已验证 | 6.5E fallback tests；online 无法验证 |
| Cache isolation | offline 已验证 | 6.5E；online 无法验证 |
| Runtime trace | offline 已验证 | 6.5E runtime trace tests；online 无法验证 |
| Independent audit | offline 已验证 | 6.5C-1 independence mutation；online 无法验证 |
| Regression | 无代码改动 | 本阶段仅探测网络，未改 production code |
| **L5 final** | **BLOCKED** | online_production_runtime_not_verified → BLOCKED |

---

## 三、L5 最终判定（第 18 节规则，原样）

```python
if proven_runtime_leakage:                    L5 = "FAIL"      # 无
elif any_reachable_runtime_tool_unverifiable: L5 = "BLOCKED"   # ← 命中
elif online_production_runtime_not_verified:  L5 = "BLOCKED"   # ← 也命中
else:                                         L5 = "PASS"
```

命中第二/三分支 → **L5 = BLOCKED**。规则未修改。

---

## 四、诚实约束（第 22 节）

- 未进入 STEP 6.6；未做预测性能/回测；未改 P5/P6/Agent graph。
- 未 silent fallback；未关闭 TLS verification；未放宽 cutoff。
- **未把 offline 当 online；未把 source capability（6.5C-1/6.5E 已 PASS）当 runtime evidence。**
- 本阶段零 production code 改动（仅探测网络 + 读 v2rayN 配置定位阻断根因）。

---

## 五、唯一前进路径（环境依赖，非代码可解）

本机 sec.gov 阻断的根因是**机场节点 + 本机 DNS 劫持组件**对 sec.gov 的专门干扰：

1. **换美国节点**：订阅有 150 节点，含多个「美国 Hysteria2」（`[vip1]⑫⑭⑯`、`[vip2]⑯`）。当前日本节点出口 IP 被 sec.gov 封禁 + DNS 劫持，美国节点可能解除。
2. 换节点后在可访问 sec.gov 的环境重跑本阶段 6 项 online 验证（probe/fundamentals/insider/PIT/no-fallback/cache-isolation/trace）。

只要 sec.gov 可达，6.5E 的 production code path（router → sec_edgar/sec_form4 → _as_of/filing_date 过滤）已 ready，可直接跑真实 online 验证并重跑 L5 aggregate。

**STOP。**

---

# 补充：STEP 6.5F-CI — 通过 GitHub Actions CI 的在线验证（2026-09-28 后续）

## 状态

```text
LOCAL WINDOWS SEC REACHABILITY   BLOCKED       （本机 DNS 劫持 + TLS 干扰，已充分探测）
CI SEC REACHABILITY              PENDING       （workflow/script/test 已建，CI 未实际运行）
OFFLINE REAL-SOURCE REPLAY       PASS          （6.5C-1 12 tests + 6.5E router-path offline replay）
ONLINE FUNDAMENTALS RUNTIME      NOT_VERIFIED  （待 CI 跑真实 SEC request）
ONLINE INSIDER RUNTIME           NOT_VERIFIED  （待 CI 跑真实 SEC request）
ACTUAL ROUTER VENDOR             sec_edgar / sec_form4（6.5E 已绑定，VENDOR_METHODS 含二者）
NO SILENT FALLBACK               PASS（offline）／PENDING（online）
RUNTIME TRACE                    PASS（offline）／PENDING（online）
INDEPENDENT AUDIT                PASS（offline，6.5C-1 independence mutation）
L5                               BLOCKED
```

## 新增交付（第 2 节允许的文件）

| 文件 | 作用 |
| --- | --- |
| `.github/workflows/step-6-5f-online.yml` | workflow_dispatch 手动触发；checkout 精确 commit；probe → verify → upload evidence |
| `scripts/step_6_5f_online.py` | `probe`（最小 reachability）+ `verify`（走 production router 的 fundamentals/insider PIT + no-fallback + cache-isolation） |
| `quant_engine/tests/oos/test_online_production_sec.py` | 7 tests：常量/hash/metadata/tag 优先级 deterministic（本地），真实 online 部分 CI-only |

## 关键设计（遵守指令纪律）

- **同一 commit**：workflow 用 `ref: ${{ github.sha }}` + script 记录 `git rev-parse HEAD`，与 Hermes 本地核对（第 29 节）。
- **复用 User-Agent 机制**：用 `SEC_EDGAR_USER_AGENT` 环境变量（sec_edgar._user_agent() 既有机制），不造第二套（第 5 节）。
- **走 production router**：`verify` 调 `route_to_vendor(...)`，不直接调 adapter（第 10/12 节）。
- **禁止 mock**：verify 全程真实 HTTP + 真实 SEC response；本地测试只测 deterministic 逻辑（tag 优先级/常量/hash），真实 online 标记 CI-only（第 7/26 节）。
- **fail-closed**：probe 失败（exit 2）→ job 失败 → verify 不执行（第 6/24 节）。
- **evidence 完整性**：manifest.json 记录每个 evidence 文件 SHA256（第 20/21 节）。

## 未完成的前置（需用户 GitHub 账号，非代码可解）

```
1. remote = https://github.com/TauricResearch/TradingAgents.git（官方仓库，只读，无 push 权限）
2. 75 文件未 commit（20 modified + 55 untracked = P1-P7 全部工作）
3. gh CLI 未安装
4. 需 fork 到用户 GitHub + push + 配置 SEC_EDGAR_USER_AGENT secret
```

**执行顺序**（待用户授权）：① commit 75 文件 → ② fork 仓库 → ③ push → ④ GitHub 配 `SEC_EDGAR_USER_AGENT` secret → ⑤ workflow_dispatch 手动触发 → ⑥ CI 跑 probe + verify → ⑦ 下载 evidence artifact 核对 SHA256 + 与本地 commit 比对 → ⑧ L5 aggregate。

**STOP（6.5F-CI 文件已备齐，CI 实际运行 pending 用户 GitHub 授权）。**
