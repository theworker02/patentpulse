# PatentPulse — USPTO Data Infrastructure Acquisition Opportunity

**5.93M** normalized records · **2018–2026** · **44** Parquet shards · **~1.6 TB** source corpus processed · weekly USPTO ingestion · resumable provenance · SQLite + JSONL + Parquet · ML/LLM-ready

| | |
| --- | --- |
| Unique records | 5,929,464 |
| Shards | 44 (train 34 · val 6 · test 4) |
| Published Parquet | 211.41 GB Zstd |
| JSONL input | 873.81 GB |
| Dedup removed | 570,714 (8.78%) |
| Core ID fill | 100% (grant id, app #, pub date, claims, doc type, source file) |
| Canonical digest | `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944` |
| Freeze | [Acquisition Release 1.0](ACQUISITION_RELEASE.md) |

## Asset

Production-oriented ingestion, normalization, provenance, validation, and release infrastructure for USPTO patent grants and published applications. Constant-memory XML streaming, identity-keyed SQLite/JSONL, global Parquet dedup, HUPD-compatible aliases, and a rights-aware Hub exporter — not a one-off scraper.

## Opportunity

Acquisition or IP transfer of PatentPulse’s **transferable software, documentation, schemas, tests, manifests/provenance system, release tooling, brand, and acquisition materials** — plus an agreed transition period. This is not merely access to public patent documents (USPTO text remains public-domain / USPTO-terms material; see [ASSET_SCHEDULE.md](ASSET_SCHEDULE.md)).

## Diligence

Acquisition data room, reproducible metrics CLI, dataset card, licensing documentation, architecture notes, corpus-finish procedure, and a **&lt;10 minute** buyer demo (fixture → ingest → query → Parquet) are available under `docs/acquisition/`.

## Engineering problem eliminated

Standing up weekly Red Book ingest is months of data engineering: concatenated dumps, DTD drift, crash-safe identity keys, torn-write JSONL, disk guards, temporal splits, and a license notice that does not pretend MIT covers every patent worldwide. PatentPulse already does that work. The buyer’s remaining product work is search, embeddings, analytics, or workflow UI on top of a finished plant and snapshot.

## Next step (no asking price)

Is PatentPulse relevant to your patent-data, AI-training, search, or IP-intelligence roadmap, and would your team be open to reviewing the acquisition materials?

Direct channel: GitHub [@theworker02](https://github.com/theworker02) · matthewlooney5@gmail.com  
Pipeline: https://github.com/theworker02/patentpulse  
Snapshot: https://huggingface.co/datasets/theworker02/patentpulse
