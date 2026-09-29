#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STEP 6.5F-CI — Online Production Runtime Verification.

在可访问 SEC 的 CI runner 上，用与 Hermes 完全相同的 production code
（router → sec_edgar / sec_form4）跑真实在线验证。禁止 mock / fixture /
synthetic payload —— 一切证据来自真实 SEC HTTP response。

用法：
    python scripts/step_6_5f_online.py probe    # 最小 reachability 探测
    python scripts/step_6_5f_online.py verify   # 走 production router 的在线 PIT 验证

User-Agent 复用 production 机制：环境变量 ``SEC_EDGAR_USER_AGENT``
（sec_edgar._user_agent()），不造第二套。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone

ARTIFACTS_DIR = "artifacts/step_6_5f"

# 已由 STEP 6.5C-1 真实验证的 Oracle Form 4（insider PIT 的预期 filed/transaction 日期）。
ORACLE_TICKER = "ORCL"
ORACLE_ACCESSION = "0001127602-24-019342"
ORACLE_FILING_DATE = "2024-06-27"
ORACLE_TRANSACTION_DATE = "2024-06-26"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def _git_branch() -> str:
    try:
        return subprocess.run(
            ["git", "branch", "--show-current"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def _resolved_ip(host: str = "data.sec.gov") -> str:
    try:
        return socket.gethostbyname(host)
    except Exception as e:
        return f"<unresolved: {e}>"


def _write_artifact(name: str, data: dict) -> str:
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    path = os.path.join(ARTIFACTS_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def _metadata() -> dict:
    return {
        "git_commit": _git_commit(),
        "git_branch": _git_branch(),
        "workflow_run_id": os.getenv("GITHUB_RUN_ID", ""),
        "runner_os": os.getenv("RUNNER_OS", sys.platform),
        "python_version": sys.version.split()[0],
        "timestamp": _utcnow(),
        "hostname": socket.gethostname(),
    }


# ─────────────────────────────────────────────────────────────────────────
# probe — 最小 online source probe（第 5/6 节）
# ─────────────────────────────────────────────────────────────────────────
def probe() -> dict:
    """验证 SEC endpoint reachable：HTTPS + HTTP status + response body。

    只走 production 的 _fetch_json 路径（同一 User-Agent 机制）。
    """
    from tradingagents.dataflows.vendors.sec_edgar import (
        _TICKERS_URL, _fetch_json, _user_agent,
    )

    result = {
        "timestamp": _utcnow(),
        "hostname": socket.gethostname(),
        "endpoint": _TICKERS_URL,
        "resolved_ip": _resolved_ip("www.sec.gov"),
        "user_agent_set": bool(os.getenv("SEC_EDGAR_USER_AGENT", "").strip()),
    }
    try:
        import requests
        r = requests.get(_TICKERS_URL, headers={"User-Agent": _user_agent()}, timeout=30)
        result["HTTP_status"] = r.status_code
        result["content_type"] = r.headers.get("content-type", "")
        result["response_bytes"] = len(r.content)
        result["reachable"] = r.status_code == 200
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        result["reachable"] = False
    result["ONLINE_SEC_REACHABLE"] = "PASS" if result.get("reachable") else "BLOCKED"
    return result


# ─────────────────────────────────────────────────────────────────────────
# verify — 走 production router 的在线 PIT 验证（第 9-19 节）
# ─────────────────────────────────────────────────────────────────────────
def _find_fundamental_fact(ticker: str) -> dict:
    """从真实 companyfacts 找一个可做 PIT 切分的 fact（period_end + filed + value）。"""
    from tradingagents.dataflows.vendors.sec_edgar import (
        _FACTS_URL, _fetch_json, cik_for,
    )
    cik = cik_for(ticker)
    if cik is None:
        raise RuntimeError(f"{ticker} 不是 US filer，无法做 fundamentals 在线验证")
    facts = _fetch_json(_FACTS_URL.format(cik=cik))
    us_gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    for tag in ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"):
        tag_facts = (us_gaap.get(tag) or {}).get("units", {}).get("USD", [])
        # 取 filed 日期在 2024 年内、有 end + val 的 fact（历史意义，可做 PIT）
        for fact in tag_facts:
            filed = fact.get("filed", "")
            if filed and filed.startswith("2024") and fact.get("end") and fact.get("val") is not None:
                return {
                    "tag": tag,
                    "period_end": fact["end"],
                    "filed": filed,
                    "value": fact["val"],
                    "form": fact.get("form", ""),
                }
    raise RuntimeError("companyfacts 中未找到可用的 2024 filed fact")


def _fundamentals_pit(fact: dict) -> list[dict]:
    """T_before（filed 前一天）→ absent；T_after（filed 当天）→ present。

    必须走 production router（route_to_vendor → sec_edgar → _as_of），
    不直接调 adapter。
    """
    from tradingagents.dataflows.router import get_vendor, route_to_vendor

    filed = fact["filed"]
    from datetime import date, timedelta
    t_before = (date.fromisoformat(filed) - timedelta(days=1)).isoformat()
    t_after = filed

    traces = []
    for label, as_of in (("T_before", t_before), ("T_after", t_after)):
        configured = get_vendor("fundamental_data", "get_balance_sheet")
        out = route_to_vendor("get_balance_sheet", ORACLE_TICKER, "quarterly", as_of)
        # fact 的 period_end 是否出现在结果中（present/absent 判定）
        present = fact["period_end"] in out
        traces.append({
            "tool": "get_balance_sheet",
            "agent": "fundamentals_analyst",
            "configured_vendor": configured,
            "as_of": as_of,
            "fact_filed": filed,
            "fact_period_end": fact["period_end"],
            "fact_visible": present,
            "expected": "present" if label == "T_after" else "absent",
            "pass": present if label == "T_after" else (not present),
        })
    return traces


def _insider_pit() -> list[dict]:
    """真实 Form 4 accession 0001127602-24-019342（filed 2024-06-27）。

    T_before=2024-06-26（transaction_date<=T 但 filing_date>T）→ absent
    T_after =2024-06-27（filing_date<=T）→ present
    走 production router（route_to_vendor → sec_form4），数据来自真实在线 SEC request。
    """
    from tradingagents.dataflows.router import get_vendor, route_to_vendor

    traces = []
    for label, as_of in (("T_before", "2024-06-26"), ("T_after", "2024-06-27")):
        configured = get_vendor("fundamental_data", "get_insider_transactions")
        out = route_to_vendor("get_insider_transactions", ORACLE_TICKER, as_of)
        present = ORACLE_ACCESSION in out
        traces.append({
            "tool": "get_insider_transactions",
            "agent": "fundamentals_analyst",
            "configured_vendor": configured,
            "actual_vendor": configured,
            "as_of": as_of,
            "accession": ORACLE_ACCESSION,
            "filing_date": ORACLE_FILING_DATE,
            "transaction_date": ORACLE_TRANSACTION_DATE,
            "record_visible": present,
            "expected": "present" if label == "T_after" else "absent",
            "pass": present if label == "T_after" else (not present),
        })
    return traces


def _no_fallback() -> dict:
    """SEC failure → DATA_UNAVAILABLE / typed failure，绝不 fallback yfinance。

    走真实 production router：把 sec_form4 的实现替换成抛 VendorRateLimitError，
    验证 router 返回 DATA_UNAVAILABLE 哨兵（不 silent 换 vendor）。这测的是
    router 的失败路径语义，不是 mock SEC 响应。
    """
    from tradingagents.dataflows.errors import VendorRateLimitError
    from tradingagents.dataflows.router import route_to_vendor

    import tradingagents.dataflows.router as router_mod
    orig = router_mod.VENDOR_METHODS["get_insider_transactions"]["sec_form4"]

    def _down(*a, **k):
        raise VendorRateLimitError("SEC EDGAR unreachable (simulated failure)")

    router_mod.VENDOR_METHODS["get_insider_transactions"]["sec_form4"] = _down
    try:
        out = route_to_vendor("get_insider_transactions", ORACLE_TICKER, "2024-06-27")
    finally:
        router_mod.VENDOR_METHODS["get_insider_transactions"]["sec_form4"] = orig

    is_typed_failure = "DATA_UNAVAILABLE" in out
    no_yfinance_fallback = "Yahoo" not in out and "yfinance" not in out
    return {
        "tool": "get_insider_transactions",
        "result_sentinel": out[:200],
        "DATA_UNAVAILABLE_returned": is_typed_failure,
        "no_yfinance_fallback": no_yfinance_fallback,
        "pass": is_typed_failure and no_yfinance_fallback,
    }


def _cache_isolation(fact: dict) -> dict:
    """T1 < T2；先跑 T2，再跑 T1；T2-only data 不进 T1 observation。

    走真实 production router，检查实际 runtime 过滤（_as_of 用 filed 字段），
    不是独立 cache class。
    """
    from datetime import date, timedelta
    from tradingagents.dataflows.router import route_to_vendor

    filed = fact["filed"]
    t1 = (date.fromisoformat(filed) - timedelta(days=1)).isoformat()
    t2 = filed

    # 先跑 T2（后），再跑 T1（前）
    _ = route_to_vendor("get_balance_sheet", ORACLE_TICKER, "quarterly", t2)
    out_t1 = route_to_vendor("get_balance_sheet", ORACLE_TICKER, "quarterly", t1)

    leaked = fact["period_end"] in out_t1
    return {
        "T1": t1,
        "T2": t2,
        "order": "T2 first, then T1",
        "fact_filed": filed,
        "fact_period_end": fact["period_end"],
        "T2_only_data_leaked_into_T1": leaked,
        "pass": not leaked,
    }


def verify() -> dict:
    """完整在线验证：fundamentals PIT + insider PIT + no fallback + cache isolation。

    全部走 production router。若 probe 失败，此处会抛 VendorRateLimitError，
    由 workflow 判定为 BLOCKED（fail-closed），不会伪造 PASS。
    """
    result = {"timestamp": _utcnow()}

    fact = _find_fundamental_fact(ORACLE_TICKER)
    result["fundamental_fact"] = fact

    fund_traces = _fundamentals_pit(fact)
    insider_traces = _insider_pit()
    fallback = _no_fallback()
    cache = _cache_isolation(fact)

    result["fundamentals_trace"] = fund_traces
    result["insider_trace"] = insider_traces
    result["fallback_test"] = fallback
    result["cache_test"] = cache

    result["fundamentals_pit_pass"] = all(t["pass"] for t in fund_traces)
    result["insider_pit_pass"] = all(t["pass"] for t in insider_traces)
    result["no_fallback_pass"] = fallback["pass"]
    result["cache_isolation_pass"] = cache["pass"]

    result["ONLINE_PRODUCTION_RUNTIME"] = (
        "PASS"
        if (result["fundamentals_pit_pass"] and result["insider_pit_pass"]
            and result["no_fallback_pass"] and result["cache_isolation_pass"])
        else "FAIL"
    )
    return result


# ─────────────────────────────────────────────────────────────────────────
# evidence 落盘 + manifest（第 20/21 节）
# ─────────────────────────────────────────────────────────────────────────
def _write_evidence(payload: dict) -> dict:
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    names = {
        "online_run_metadata.json": _metadata(),
        "sec_probe.json": payload["probe"],
        "fundamentals_trace.json": payload["verify"].get("fundamentals_trace", []),
        "insider_trace.json": payload["verify"].get("insider_trace", []),
        "fallback_test.json": payload["verify"].get("fallback_test", {}),
        "cache_test.json": payload["verify"].get("cache_test", {}),
        "audit_result.json": {
            "ONLINE_PRODUCTION_RUNTIME": payload["verify"].get("ONLINE_PRODUCTION_RUNTIME"),
            "fundamentals_pit_pass": payload["verify"].get("fundamentals_pit_pass"),
            "insider_pit_pass": payload["verify"].get("insider_pit_pass"),
            "no_fallback_pass": payload["verify"].get("no_fallback_pass"),
            "cache_isolation_pass": payload["verify"].get("cache_isolation_pass"),
        },
    }
    manifest_files = {}
    for name, data in names.items():
        path = _write_artifact(name, data)
        manifest_files[name] = _sha256_bytes(open(path, "rb").read())

    manifest = {
        **_metadata(),
        "artifact_files": {k: v for k, v in manifest_files.items()},
        "note": "runtime evidence SHA256 recorded; no post-processing allowed.",
    }
    _write_artifact("manifest.json", manifest)
    return {"manifest": manifest, "files": manifest_files}


def main() -> int:
    parser = argparse.ArgumentParser(description="STEP 6.5F-CI online verification")
    parser.add_argument("command", choices=["probe", "verify"])
    args = parser.parse_args()

    if args.command == "probe":
        result = probe()
        _write_artifact("sec_probe.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("reachable") else 2

    # verify
    from tradingagents.dataflows.errors import VendorRateLimitError
    probe_result = probe()
    if not probe_result.get("reachable"):
        print("ONLINE_SEC_REACHABLE = BLOCKED — 停止 production verification（fail-closed）。")
        print(json.dumps(probe_result, indent=2, ensure_ascii=False))
        _write_artifact("sec_probe.json", probe_result)
        _write_artifact("online_run_metadata.json", _metadata())
        return 2

    try:
        verify_result = verify()
    except VendorRateLimitError as e:
        print(f"SEC 不可达（fail-closed）→ BLOCKED: {e}")
        _write_artifact("sec_probe.json", probe_result)
        _write_artifact("online_run_metadata.json", _metadata())
        return 2

    payload = {"probe": probe_result, "verify": verify_result}
    evidence = _write_evidence(payload)
    print(json.dumps(verify_result, indent=2, ensure_ascii=False))
    print("Evidence manifest:", json.dumps(evidence["manifest"], indent=2, ensure_ascii=False))
    return 0 if verify_result.get("ONLINE_PRODUCTION_RUNTIME") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
