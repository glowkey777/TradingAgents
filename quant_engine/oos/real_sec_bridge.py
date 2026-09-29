# -*- coding: utf-8 -*-
"""Real SEC Source Evidence Bridge（P7 STEP 6.5C-1）。

真实 SEC raw response → 原样保存 → SHA256 → provenance → parser → AvailabilityEvidence。
fixture 必须来自真实 SEC response，禁止 synthetic reconstruction。

raw 文件 byte-for-byte 原样保存（*.raw）；provenance 在 MANIFEST.json；
parser 中间结构另存 parsed.json，不能代替 raw evidence。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .availability_models import AvailabilityEvidence, AvailabilityStatus, utc_iso

# 真实样本目录（相对 quant_engine/oos/ 的上级 tests/oos/fixtures/real_sec/）
REAL_SEC_DIR = Path(__file__).resolve().parent.parent / "tests" / "oos" / "fixtures" / "real_sec"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_manifest() -> list[dict]:
    """加载 MANIFEST.json（样本列表）。无 manifest → []。"""
    manifest_path = REAL_SEC_DIR / "MANIFEST.json"
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_raw_sample(sample: dict) -> tuple[bytes, dict]:
    """加载单个真实样本的 raw bytes + metadata，并校验 SHA256。"""
    raw_path = REAL_SEC_DIR / sample["raw_file"]
    raw = raw_path.read_bytes()
    expected = sample.get("content_sha256")
    if expected and sha256_bytes(raw) != expected:
        raise ValueError(
            f"SHA256 mismatch for {sample['raw_file']}: "
            f"expected {expected[:16]}... got {sha256_bytes(raw)[:16]}..."
        )
    return raw, sample


def load_sample_file(sample: dict, key: str) -> bytes:
    """加载样本的某个文件（raw_file / xml_file / header_file），返回 bytes。"""
    fn = sample.get(key)
    if not fn:
        raise FileNotFoundError(f"sample 缺 {key} 字段")
    return (REAL_SEC_DIR / fn).read_bytes()


def parse_submissions_form4_filing_date(raw: bytes) -> str | None:
    """从 SEC submissions API raw JSON 提取 Form 4 的 filingDate。

    raw 是 filings.recent columnar array（form/filingDate/accessionNumber 同索引对齐）。
    返回第一个 form in ("4", "4/A") 的 filingDate，无则 None。
    """
    d = json.loads(raw.decode("utf-8"))
    recent = d.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    for i in range(min(len(forms), len(dates))):
        if forms[i] in ("4", "4/A"):
            return dates[i]
    return None


# ── Form 4 XML + submission header parser（真实 complete-submission）──

def parse_form4_xml_transaction_date(xml: bytes) -> str | None:
    """从真实 Form 4 XML 提取 transactionDate（第一个 nonDerivativeTransaction）。"""
    text = xml.decode("utf-8", "replace")
    m = re.search(r"<transactionDate>\s*<value>([^<]+)</value>", text)
    return m.group(1).strip() if m else None


def parse_submission_header_filing_date(header: str) -> str | None:
    """从真实 SEC submission header 提取 FILED AS OF DATE（YYYYMMDD → YYYY-MM-DD）。"""
    m = re.search(r"FILED AS OF DATE:\s*(\d{8})", header)
    if not m:
        return None
    d = m.group(1)
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}"


def parse_submission_header_accession(header: str) -> str | None:
    m = re.search(r"ACCESSION NUMBER:\s*([0-9-]+)", header)
    return m.group(1).strip() if m else None


def parse_submission_header_acceptance_datetime(header: str) -> str | None:
    m = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", header)
    if not m:
        return None
    d = m.group(1)
    return f"{d[:4]}-{d[4:6]}-{d[6:8]} {d[8:10]}:{d[10:12]}:{d[12:14]}"


# ── 统一 evidence 生成 ──

def raw_to_filing_evidence(
    raw: bytes,
    sample: dict,
    as_of: str,
) -> AvailabilityEvidence:
    """真实 raw + provenance → AvailabilityEvidence。

    filing_date 真实来自 source parser（submissions JSON 或 submission header），
    不是 fixture 手填；transaction_date 从 form4.xml 解析，绝不当作 available_at。
    """
    if sample.get("header_file"):
        header = load_sample_file(sample, "header_file").decode("utf-8", "replace")
        filing_date = parse_submission_header_filing_date(header)
        source_field = "FILED AS OF DATE"
        record_id = sample.get("accession_number") or parse_submission_header_accession(header) or "unknown"
    else:
        filing_date = parse_submissions_form4_filing_date(raw)
        source_field = "filingDate"
        record_id = sample.get("accession_number") or "unknown"

    if filing_date is None:
        return AvailabilityEvidence(
            status=AvailabilityStatus.UNVERIFIABLE,
            available_at=None, source="sec_edgar", source_field=None,
            record_id=record_id, as_of=utc_iso(as_of),
            reason="真实 raw 中无 filing date，available_at 无法建立",
        )

    if utc_iso(filing_date) > utc_iso(as_of):
        return AvailabilityEvidence(
            status=AvailabilityStatus.VIOLATION,
            available_at=utc_iso(filing_date),
            source="sec_edgar", source_field=source_field,
            record_id=record_id, as_of=utc_iso(as_of),
            reason=f"真实 filing_date={filing_date} > T（未来 filing，不可见）",
        )

    return AvailabilityEvidence(
        status=AvailabilityStatus.PROVEN,
        available_at=utc_iso(filing_date),
        source="sec_edgar", source_field=source_field,
        record_id=record_id, as_of=utc_iso(as_of),
        reason=f"真实 Form 4 filing_date={filing_date} <= T（提交即公开）",
    )


def verify_manifest_integrity() -> list[str]:
    """校验 MANIFEST.json 中所有样本的 SHA256 与磁盘文件一致。返回不匹配列表。"""
    errors = []
    for sample in load_manifest():
        for key in ("raw_file", "xml_file", "header_file"):
            fn = sample.get(key)
            if not fn:
                continue
            path = REAL_SEC_DIR / fn
            if not path.exists():
                errors.append(f"{fn}: 文件缺失")
                continue
            expected = sample.get(f"{key.removesuffix('_file')}_sha256") or sample.get("content_sha256")
            if expected and sha256_file(path) != expected:
                errors.append(f"{fn}: SHA256 不匹配")
    return errors
