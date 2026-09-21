# Historical corpus finish procedure

**Freeze context:** Acquisition Release 1.0 ships a measured **partial** 2018–2026 snapshot: **5,929,464** unique records across **44** Parquet shards with publication years spanning **2018–2026**. That is not the same claim as “every USPTO weekly ZIP in range is `complete` in the operator manifest.”

This document states precisely what remains, the storage/compute budget, and the automated finish path so a buyer (or the seller before close) can drive coverage to 100% without improvising.

## 1. What the frozen snapshot already contains

| Dimension | Included in Acquisition Release 1.0 |
| --- | --- |
| Unique Parquet records | 5,929,464 |
| Shards | 44 |
| Publication years present | 2018, 2019, 2020, 2021, 2022, 2023, 2024 (train); 2025 (validation); 2026+ (test) |
| Formats | SQLite/JSONL plant + published Zstd Parquet |
| Provenance | Hub `release_manifest.json` digest `42d3a4ae…4944` |
| Weekly ZIP completeness | **Not asserted** — tracked only in private `data/manifest.json` |

## 2. What remains (two independent finish tracks)

### Track A — Weekly archive completeness (catalog vs manifest)

**Remaining work:** every USPTO `PTGRXML` (grants) and `APPXML` (applications) weekly file whose publication/file date falls in the operator backfill window (default **2018-01-01 → today**) and is not yet `status=complete` in `data/manifest.json`.

**How to measure (authoritative):**

```bash
export USPTO_API_KEY="..."   # https://data.uspto.gov/apis/getting-started
python -m patentpulse.coverage --from-date 2018-01-01 --json docs/acquisition/metrics/coverage_report.json
```

Without an API key, the same command emits a **calendar estimate** of expected Tuesday grant / Thursday application weeks (planning only; ODP is authoritative).

**Important:** a fresh git clone has an empty `data/manifest.json`. Coverage will then report ~910 missing archives for 2018-01-01→2026-09-21 even though the **published Hub snapshot already holds 5.93M unique records**. Run coverage on the **operator host** that owns the production manifest to see residual weeks. The checked-in `metrics/coverage_report.json` from Acquisition Release 1.0 documents the calendar envelope and resource model for that empty-manifest evaluation clone.

**Planning envelope (calendar, both products, 2018-01-01 → 2026-09-21):**

| Estimate | Value |
| --- | ---: |
| Approximate grant Tuesdays | ~455 |
| Approximate application Thursdays | ~455 |
| Approximate weekly archives in window | **~910** |
| Frozen unique records already released | 5,929,464 |
| Unknown until coverage report | Exact `complete` / `pending` / `failed` counts on the operator host |

The coverage CLI writes those exact counts when run against the live manifest + ODP listing.

### Track B — Bibliographic re-extract (~40% schema-evolution gap)

About **39.7%** of published rows lack later bibliographic columns (`kind_code`, `filing_date`, inventors, `claim_count`, …) because those fields were added after part of the append-only JSONL was written ([QUALITY_METRICS.md](QUALITY_METRICS.md)). Core IDs and full text remain high-fill.

**Remaining work (optional product requirement):** re-ingest historical weeks with the current parser (`ingest sync --force` per week or rebuild JSONL from retained/re-fetched ZIPs), then cut a new Parquet release.

## 3. Storage and compute requirements

### Persistent (finish + re-publish)

| Resource | Budget |
| --- | --- |
| Published Parquet (current) | **~212 GB** |
| Local JSONL if retained at current scale | **~874 GB** |
| Local SQLite (optional) | typically smaller than JSONL; budget **≥200 GB** free for growth |
| Working headroom for exporter | decoded estimate × 1.2, minimum 2 GB free ([docs/HF_RELEASE.md](../HF_RELEASE.md)) |

### Transient (weekly sync)

| Resource | Budget |
| --- | --- |
| One weekly ZIP on disk | hundreds of MB to a few GB (deleted after success unless `--keep-raw`) |
| Concurrent weeks | keep at **1** ZIP resident unless the operator widens parallelism |
| Full raw corpus if all ZIPs retained | on the order of **~1.6 TB** (project estimate; not re-weighed in this VM) |

### Compute (single 4-vCPU class host, size-adjusted)

| Job | Estimate |
| --- | --- |
| Fixture parser overhead (measured) | **1,465 docs/s** ([INGESTION_BENCHMARK.md](INGESTION_BENCHMARK.md)) |
| Full-text planning throughput | **~19 docs/s** |
| Re-parse 5.93M full-text records | **~3.6 days** CPU wall on one process |
| Weekly incremental (~6k–10k docs) | **minutes** |
| Finish remaining weeks | dominated by **download + parse per missing ZIP**; run unattended via `ingest sync` |

Shard by week across machines if faster wall-clock is required; the parser is constant-memory per document.

## 4. Automated finish procedure

### Step 0 — Baseline

```bash
python -m pytest tests -q
python -m patentpulse.ingest status
python -m patentpulse.coverage --from-date 2018-01-01 \
  --json docs/acquisition/metrics/coverage_report.json
```

Stop and triage if `files_failed > 0` or coverage reports persistent fetch errors.

### Step 1 — Drive weekly completeness (Track A)

```bash
export USPTO_API_KEY="..."
# Repeat until coverage reports 0 missing (or wrap with scripts/finish_corpus.sh)
python -m patentpulse.ingest sync --source both --format both --weeks 20
python -m patentpulse.coverage --from-date 2018-01-01 \
  --json docs/acquisition/metrics/coverage_report.json
```

Behavior relied upon:

- Completed weeks are skipped.
- Stale `running` rows are recovered.
- Process lock prevents overlapping syncs.
- Archives are deleted after success unless `--keep-raw`.

Or one-shot helper:

```bash
./scripts/finish_corpus.sh --from-date 2018-01-01 --weeks-per-batch 20
```

### Step 2 — Optional bibliographic rebuild (Track B)

Only if late bibliographic fill is a product requirement:

```bash
# Re-fetch/re-parse weeks that predate the schema expansion, then:
python -m patentpulse.hf_release export \
  --input data/processed/patents.jsonl \
  --output /data/releases/patentpulse-complete \
  --skip-invalid-json
python -m patentpulse.hf_release validate --release /data/releases/patentpulse-complete
```

### Step 3 — Acceptance gates

| Gate | Pass criteria |
| --- | --- |
| Coverage | `missing_archives == 0` for both products in the chosen date window **or** an explicit, dated waiver listing residual gaps |
| Manifest | `ingest status` shows 0 pending / running / failed |
| Tests | `pytest tests -q` green |
| Release | `hf_release validate` green; new digest recorded |
| Metrics | `python -m patentpulse.metrics ...` refreshed into `docs/acquisition/metrics/` |

### Step 4 — Freeze the completed corpus

Update [ACQUISITION_RELEASE.md](ACQUISITION_RELEASE.md) (or cut `acquisition-release-1.1`) with the new record counts, shard counts, digest, and coverage report path. Do not edit `manifest.json` to fake completeness.

## 5. Honest buyer language (replace “backfill in progress”)

Preferred freeze wording:

> Acquisition Release 1.0 includes **5,929,464** unique USPTO full-text records with publication years **2018–2026** across **44** Parquet shards. Weekly catalog completeness is an operator finish job with an automated coverage report and `ingest sync` procedure; residual missing weeks (if any) are enumerated by `python -m patentpulse.coverage` on the deploy host.

Avoid unqualified “backfill in progress” without pointing at this procedure and the coverage artifact.
