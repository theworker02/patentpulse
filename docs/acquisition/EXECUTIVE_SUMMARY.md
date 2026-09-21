# Executive summary

PatentPulse is a production USPTO full-text pipeline plus an immutable 5.93 million-record Parquet snapshot. An acquirer does not buy a scraper. They buy a finished weekly ingest loop, a normalized schema with HUPD-compatible aliases, global identity deduplication, and a citable Hub package.

## Headline metrics (measured 2026-09-21)

| Metric | Value | Source |
| --- | --- | --- |
| Unique released records | **5,929,464** | `release_manifest.json` |
| Valid JSONL rows seen | 6,500,178 | same |
| Duplicates removed | 570,714 (**8.78%**) | same; `seen - duplicates = written` |
| Malformed JSONL rows skipped | 186 (**0.00286%** of attempted rows) | same |
| Unique yield of valid JSON | **91.22%** | 5,929,464 / 6,500,178 |
| Uncompressed JSONL input | **873.81 GB** (813.80 GiB) | `source_bytes` |
| Published Zstd Parquet | **211.41 GB** (196.89 GiB, 44 files) | Hub tree |
| Decoded Parquet page bytes | **970.25 GB** | footers of all 44 shards |
| Parquet page compression | **21.77%** of decoded pages | compressed / uncompressed pages |
| JSONL → Parquet file ratio | **24.19%** remaining | 211.41 / 873.81 |
| Core ID fill rate | **100%** grant id, application number, publication date, claims, document type, source file | Parquet statistics, 5.93M rows |
| Title / description / abstract | 99.89% / 99.11% / 94.67% | same |
| Primary CPC | 94.61% | same |
| Local ingest throughput | **1,465 docs/s** (2,000 unique fixture documents, SQLite+JSONL, 4 vCPU) | `ingestion_benchmark.json` |
| Replay dedup | **2,000/2,000 skipped**, 0 new writes | second pass on the same SQLite file |

## Why this is an acquisition, not a weekend project

A serious internal USPTO corpus is not "download some XML." It is concatenated weekly dumps, evolving DTDs, constant-memory parsing, identity keys that survive crashy backfills, legal boilerplate stripping that does not destroy notation, a stable Arrow schema, temporal splits, and a rights notice that does not pretend MIT covers every patent document worldwide. PatentPulse already does that work. The remaining product work for a buyer is search, embeddings, or workflow UI on top of a finished dataset.

## Two buyer paths

1. **Consume the snapshot** (hours): `load_dataset("theworker02/patentpulse")` after applying the empty-split Hub card fix in [HUB_VIEWER_FIX.md](HUB_VIEWER_FIX.md).
2. **Take the pipeline** (days to wire, then resumable backfill): `python -m patentpulse.ingest sync` with a USPTO Open Data Portal key. See [BUYER_DEPLOYMENT.md](BUYER_DEPLOYMENT.md).

## What is not claimed

- The snapshot is a 2026-08-28 historical partial of the 2018–2026 backfill, not a claim that every USPTO week is present.
- Fixture throughput is not full-text production throughput. Production records average ~147 KB of JSONL versus ~2 KB in the benchmark fixture; size-adjusted ingest is discussed in [INGESTION_BENCHMARK.md](INGESTION_BENCHMARK.md).
- This is not legal advice, validity, infringement, or patentability data.
