# Acquisition Brief — PatentPulse

**Date:** 2026-09-21  
**Status:** Briefing document only. **No acquisition has occurred** by virtue of this file.

## What the project does

USPTO full-text ingestion pipeline plus an immutable **5.93 million-record** Parquet snapshot: weekly grant and application XML dumps are streamed, normalized, deduplicated, and published for search, NLP, and model training.

## Problem

Building a serious local USPTO corpus is not “download some XML.” It requires evolving DTDs, constant-memory parsing, crash-safe identity keys, legal boilerplate stripping, a stable schema, and a rights notice that does not pretend open-source licenses cover every patent document worldwide.

## Headline metrics (measured 2026-09-21)

| Metric | Value |
| --- | --- |
| Unique released records | **5,929,464** |
| Valid JSONL rows seen | 6,500,178 |
| Duplicates removed | 570,714 (**8.78%**) |
| Malformed JSONL rows skipped | 186 (**0.00286%**) |
| Unique yield of valid JSON | **91.22%** |
| Uncompressed JSONL input | **873.81 GB** |
| Published Zstd Parquet | **211.41 GB** (44 shards) |
| Publication years | **2018–2026** |
| Core ID fill rate | **100%** (grant id, application number, publication date, claims, document type, source file) |
| Local ingest throughput (fixture) | **1,465 docs/s** |

Full measured packet: [`docs/acquisition/EXECUTIVE_SUMMARY.md`](docs/acquisition/EXECUTIVE_SUMMARY.md).

## What is included in a transaction (typical)

- Git repository and original PatentPulse pipeline / docs (subject to agreement)
- Asserted copyright in original works (subject to counsel / chain of title)
- Branding assets created for PatentPulse
- Acquisition data room under `docs/acquisition/`
- Rights to continue and redistribute the published Hub snapshot under the data notice (subject to USPTO and applicable law)

## What is NOT included

- Ownership of USPTO-originated patent text and bibliographic records
- Historical evaluation grants already received by third parties
- Third-party dependency source
- Buyer cloud accounts, USPTO API keys, or Hugging Face tokens
- Fabricated user/revenue metrics (none claimed)
- An asking price (none published)

## Maturity

**PatentPulse Acquisition Release 1.0** — production weekly ingest loop, HUPD-compatible field aliases, global identity deduplication, and a citable Hub package. Single human maintainer.

## Deployment model

Two buyer paths:

1. **Consume the snapshot** — `load_dataset("theworker02/patentpulse")` ([Hugging Face](https://huggingface.co/datasets/theworker02/patentpulse))
2. **Take the pipeline** — `python -m patentpulse.ingest sync` with a USPTO Open Data Portal key

Local SQLite inspection without a full Hub download: `python -m patentpulse.peek`. Fifteen-minute evaluation: [`docs/BUYER_QUICKSTART.md`](docs/BUYER_QUICKSTART.md).

## Technical differentiation

Official weekly source archives with per-file provenance; grants and applications in one corpus; resumable backfill; immutable Parquet release with measured quality metrics — not a one-off scrape.

## Diligence pointers

Start in [`docs/acquisition/`](docs/acquisition/README.md) — especially:

- [EXECUTIVE_SUMMARY.md](docs/acquisition/EXECUTIVE_SUMMARY.md)
- [TEASER.md](docs/acquisition/TEASER.md)
- [ASSET_SCHEDULE.md](docs/acquisition/ASSET_SCHEDULE.md)
- [BUYER_DEMO.md](docs/acquisition/BUYER_DEMO.md)
- [BUYER_DEPLOYMENT.md](docs/acquisition/BUYER_DEPLOYMENT.md)
- [ACQUISITION_RELEASE.md](docs/acquisition/ACQUISITION_RELEASE.md)

## Acquisition contact

GitHub [@theworker02](https://github.com/theworker02) · https://github.com/theworker02/patentpulse

No valuation is stated in this document.
