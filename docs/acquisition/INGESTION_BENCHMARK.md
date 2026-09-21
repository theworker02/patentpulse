# Ingestion throughput benchmark

Reproducible CPU-bound parse benchmark (no USPTO network). Measured on the
cloud-agent host used to build this data room.

## How to reproduce

```bash
python scripts/benchmark_ingestion.py \
  --docs 2000 \
  --batch-size 200 \
  --output docs/acquisition/metrics/ingestion_benchmark.json
```

The script expands `tests/fixtures/sample_bulk.xml` into N documents with
**unique** grant/application IDs so SQLite identity dedup does not collapse
the workload.

## Results (2026-09-21)

| Host | `Linux-6.12.94+ x86_64`, Python 3.12.3 |
| --- | --- |
| Input | 2,000 docs · 6.592 MB synthetic bulk |

| Stage | Docs/s | Input MB/s | Notes |
| --- | --- | --- | --- |
| Extract only (stream + `extract_patent_from_xml`) | **1,646.5** | 5.43 | No DB/JSONL writes |
| End-to-end SQLite + JSONL | **1,517.5** | 5.00 | `documents_failed=0`, `records_skipped=0` |

Artifact: [metrics/ingestion_benchmark.json](metrics/ingestion_benchmark.json).

## Scaling notes for buyers

1. Fixture documents are **small** relative to full utility patents (typical
   description p50 ≈ 47k characters in the Hub sample). Expect lower docs/s
   on production weekly ZIPs; throughput in **MB/s of XML** is the stabler
   planner metric.
2. Network download from USPTO ODP and ZIP decompression add wall time outside
   this benchmark.
3. Weekly grant/application files contain on the order of thousands of
   documents; at ~10³ docs/s parse, a single week is typically minutes of CPU
   after download on a modern x86_64 box.
4. Order-of-magnitude full backfill: with continuous sync, wall clock is
   dominated by download quotas, disk, and operator uptime — not by the XML
   parser once hardware is provisioned.

## Suggested buyer benchmark add-ons

- Time one real `ipg*.zip` / `ipa*.zip` through
  `python -m patentpulse.parse --format both`.
- Record `docs_per_s` and `input_MB_per_s` in your diligence worksheet.
- Re-run `scripts/benchmark_ingestion.py` on the target deploy SKU for an
  apples-to-apples comparison with this data room.
