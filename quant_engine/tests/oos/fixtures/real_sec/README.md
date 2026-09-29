# real_sec — 真实 SEC Source Evidence

此目录存放**真实 SEC EDGAR raw response**（byte-for-byte 原样保存）。
禁止 synthetic reconstruction / 手填字段 / 根据文档结构自行构造。

## 如何导入真实样本

1. 在**网络可达 sec.gov 的环境**（你自己的机器 / 独立环境）获取真实 raw：

   ```bash
   # 方式 1：submissions API（含 Form 4 filingDate）
   curl -H "User-Agent: <你的名字> <email>" \
     "https://data.sec.gov/submissions/CIK0000320193.json" \
     -o sample_form4_001.raw

   # 方式 2：单个 Form 4 filing 的 XML（含 transaction_date + filing_date）
   # 从 submissions 拿 accessionNumber，再下载 XML
   ```

2. 把 raw 文件放到本目录，**不改名不重排不删字段**。

3. 计算 SHA256 并写入 MANIFEST.json：

   ```bash
   sha256sum sample_form4_001.raw
   ```

4. 每个样本在 MANIFEST.json 中登记（见下方 schema）：

   ```json
   {
     "sample_id": "sample_form4_001",
     "source": "SEC EDGAR submissions",
     "source_url": "https://data.sec.gov/submissions/CIK0000320193.json",
     "retrieved_at": "2026-09-28T00:00:00Z",
     "content_sha256": "<64 hex>",
     "content_type": "application/json",
     "http_status": 200,
     "ticker": "AAPL",
     "cik": "0000320193",
     "accession_number": "0000320193-24-000050",
     "form": "4",
     "filing_date": "2024-06-10",
     "filing_date_source_field": "filingDate",
     "raw_file": "sample_form4_001.raw"
   }
   ```

   `filing_date` 必须来自 raw source 的真实字段（`filingDate`），不能手填推断。

## 关键规则（用户 verbatim）

- `*.raw` = byte-for-byte source payload（JSON 存原始 bytes，XML 存原始 XML bytes）
- parsed 中间结构另存 `parsed.json`，不能代替 raw evidence
- **只改变 replay cutoff（as_of），不能修改 raw response**
- 真实样本不足时，测试 skip（不 fail）；真实样本导入后才跑 replay

## 样本要求

- 至少 1 个真实 Form 4（最好 2 个：A=transaction<filing<=T，B=transaction<=T<filing）
- 若找不到天然满足 Sample B 的记录，用真实 filing_date 构造 replay cutoff（只改 as_of）
