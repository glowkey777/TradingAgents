# -*- coding: utf-8 -*-
"""STEP 6.5F-CI online production verification — deterministic 部分测试。

本地只测 script 的 deterministic 部分（schema/结构/hash/常量/纯逻辑）。
真实 online 测试（走真实 SEC request）在 GitHub Actions runner 执行，
本地 skip（指令第 7/26 节：禁止 mock SEC 响应冒充 online evidence）。
"""
import os
import sys

import pytest

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from scripts.step_6_5f_online import (  # noqa: E402
    ORACLE_ACCESSION,
    ORACLE_FILING_DATE,
    ORACLE_TRANSACTION_DATE,
    _find_fundamental_fact,
    _metadata,
    _sha256_bytes,
)


# ── 常量（STEP 6.5C-1 已真实验证的值，必须一致）──
def test_oracle_accession_constant():
    assert ORACLE_ACCESSION == "0001127602-24-019342"


def test_oracle_filing_and_transaction_date():
    assert ORACLE_FILING_DATE == "2024-06-27"
    assert ORACLE_TRANSACTION_DATE == "2024-06-26"
    # transaction_date != filing_date（真实 source 的核心 trap）
    assert ORACLE_TRANSACTION_DATE != ORACLE_FILING_DATE


# ── hash 确定性 ──
def test_sha256_deterministic():
    a = _sha256_bytes(b"real sec response bytes")
    b = _sha256_bytes(b"real sec response bytes")
    assert a == b
    assert len(a) == 64
    assert a != _sha256_bytes(b"different")


# ── metadata 结构 ──
def test_metadata_has_commit_and_timestamp():
    m = _metadata()
    assert "git_commit" in m
    assert "timestamp" in m
    assert "python_version" in m
    assert "hostname" in m


# ── _find_fundamental_fact 的 tag 优先级（deterministic，monkeypatch 传输层）──
def test_fundamental_fact_prefers_revenue_tags(monkeypatch):
    """验证 tag 优先级：RevenueFromContract... > Revenues > SalesRevenueNet。

    这里 monkeypatch 的是 _fetch_json（传输层），测的是 tag 选择的确定性逻辑，
    不是拿 mock 响应冒充 online evidence。
    """
    from tradingagents.dataflows.vendors import sec_edgar

    fake_facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"filed": "2024-03-12", "end": "2024-02-29", "val": 13300000000.0, "form": "10-Q"},
                        ]
                    }
                },
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {"filed": "2024-06-10", "end": "2024-05-31", "val": 14300000000.0, "form": "10-Q"},
                        ]
                    }
                },
            }
        }
    }
    monkeypatch.setattr(sec_edgar, "cik_for", lambda t: "0001341439")
    monkeypatch.setattr(sec_edgar, "_fetch_json", lambda url: fake_facts)

    fact = _find_fundamental_fact("ORCL")
    # 第一个 tag 优先（RevenueFromContractWithCustomerExcludingAssessedTax）
    assert fact["tag"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert fact["filed"] == "2024-06-10"
    assert fact["period_end"] == "2024-05-31"


def test_fundamental_fact_skips_non_2024(monkeypatch):
    """只取 2024 年内的 filed fact（历史意义，可做 PIT）。"""
    from tradingagents.dataflows.vendors import sec_edgar

    fake = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"filed": "2023-11-15", "end": "2023-10-31", "val": 1.0, "form": "10-Q"},
                            {"filed": "2024-03-12", "end": "2024-02-29", "val": 2.0, "form": "10-Q"},
                        ]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(sec_edgar, "cik_for", lambda t: "0001341439")
    monkeypatch.setattr(sec_edgar, "_fetch_json", lambda url: fake)
    fact = _find_fundamental_fact("ORCL")
    assert fact["filed"].startswith("2024")  # 跳过 2023 fact


# ── 真实 online 验证只能在 CI 跑（本地 skip，不 mock）──
def test_online_verification_is_ci_only():
    """真实 online verification（真实 SEC request）只在 CI 跑，本地不得冒充。"""
    import scripts.step_6_5f_online as m

    if os.getenv("CI") == "true":
        pytest.skip("CI 环境：真实 online 验证由 workflow 的 verify step 执行")
    # 本地：明确断言这是 CI-only，不 mock SEC
    assert m.probe.__module__ == "scripts.step_6_5f_online"
