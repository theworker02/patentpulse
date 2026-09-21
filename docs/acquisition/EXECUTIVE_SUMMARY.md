# Executive summary — PatentPulse for acquirers

PatentPulse is a **production USPTO full-text ingestion system** plus a
**5.93M-record immutable Parquet snapshot** covering grants and published
applications (2018–2026 backfill window). It turns weekly official XML dumps
into search-, RAG-, and training-ready text with per-archive provenance.

## Why acquire instead of rebuild

An in-house team rebuilding this typically spends months on:

| Workstream | What PatentPulse already ships |
| --- | --- |
| ODP catalog + weekly sync | Resumable sync with rate-limit retries, size checks, process lock |
| Concatenated XML streaming | Constant-memory document splitter for multi-GB weekly ZIPs |
| Field normalization | Title, abstract, claims, description, CPC/IPC, citations, inventors |
| Crash-safe writers | SQLite WAL + append JSONL with stable identity dedup |
| Publish path | Guarded Zstd Parquet exporter, temporal splits, content digest |
| Provenance | Per-file URL, SHA-256, parse/fail counts in the ingest manifest |

**Buyer value proposition:** skip the data-engineering runway and plug a
validated corpus + continuous updater into an existing patent-intelligence,
legal-AI, prior-art, or scientific-information product.

## Headline numbers (measured 2026-09-21)

| Metric | Value |
| --- | --- |
| Unique released records | 5,929,464 |
| JSONL source (uncompressed textual corpus) | **873.8 GB** |
| Published Parquet on Hub (compressed) | **211.4 GB** (44 shards) |
| Estimated Parquet uncompressed | **~966.7 GB** |
| Hub vs JSONL compression ratio | 0.242 |
| Release duplicates removed | 570,714 (**8.78%** of rows seen) |
| Malformed JSONL rows skipped | 186 (**0.0029%**) |
| Parse throughput (fixture-scale e2e, Linux x86_64) | **~1,517 docs/s** |
| Claims coverage (quality sample) | **100%** nonempty |
| Description coverage (quality sample) | **99.3%** nonempty |
| Abstract coverage (quality sample) | **90.9%** nonempty |
| Primary CPC coverage (quality sample) | **90.8%** nonempty |

Sources: `docs/acquisition/metrics/acquisition_metrics.json`,
`docs/acquisition/metrics/ingestion_benchmark.json`.

## Known diligence flags (disclosed)

1. **Bibliographic sparsity in the published v1 snapshot.** Sampled Hub rows
   show empty `kind_code`, `filing_date`, `inventor_list`, `assignee_names`,
   and citation lists. The **current** extractor and unit tests populate these
   fields; they were largely absent from the historical append-only JSONL that
   fed the 2026-08-28 release. Remedy: re-ingest weeks of interest and
   re-export (see [BUYER_DEPLOYMENT.md](BUYER_DEPLOYMENT.md)).
2. **Not patent-family deduplicated.** Grants and applications can describe
   related inventions; identity is publication/application keyed.
3. **No images, sequences as structured modalities, or prosecution outcomes.**
4. **Data rights are USPTO-sourced `other`**, not a blanket commercial license
   for every jurisdiction — see [DATA_LICENSE.md](../../DATA_LICENSE.md).

## Transfer package

- GitHub repository (MIT code + docs)
- Hugging Face dataset snapshot (or private mirror)
- This acquisition data room
- Optional: operator knowledge transfer for ODP keys, storage sizing, release cadence

## Next step for buyers

1. Stream a shard: `load_dataset("theworker02/patentpulse", split="train", streaming=True)`
2. Run [BUYER_DEPLOYMENT.md](BUYER_DEPLOYMENT.md) smoke path on a single weekly ZIP
3. Schedule a technical diligence call using the metrics JSON as the agenda
