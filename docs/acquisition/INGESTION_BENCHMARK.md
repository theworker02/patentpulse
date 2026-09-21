# Ingestion throughput benchmark

Measured 2026-09-21 on the machine recorded in [metrics/environment.json](metrics/environment.json).

## Hardware

| Item | Value |
| --- | --- |
| CPU | Intel Xeon, 4 logical processors |
| Memory | 16.79 GB |
| OS | Linux 6.12.94+ x86_64, glibc 2.39 |
| Python | 3.12.3 |
| Output | SQLite WAL + JSONL, batch size 250 |

This is a cloud-agent VM, not a tuned ingest box. Treat the numbers as a lower bound a buyer can reproduce, not as a peak-cluster claim.

## Reproducing the run

```bash
python -m patentpulse.metrics --output docs/acquisition/metrics --documents 2000
```

The command expands `tests/fixtures/sample_bulk.xml` into unique USPTO-like documents, parses them with the production `parse_bulk_file` path, then replays the unique file into the same SQLite database.

## Unique-file pass (2,000 distinct identities)

| Metric | Value |
| --- | ---: |
| Documents seen | 2,000 |
| Documents parsed | 2,000 |
| Documents failed | 0 |
| Records written | 2,000 |
| Records skipped | 0 |
| Wall time | 1.365 s |
| Throughput | **1,465.3 docs/s** |
| Unique JSONL bytes | 3,895,000 |
| Unique SQLite bytes | 2,248,704 |

## Mixed-file pass (production-like error mix)

Configured: 2,000 patent docs, 8% duplicate identities (160), 25 unknown-root sequence listings, 5 truncated XML documents.

| Metric | Value |
| --- | ---: |
| Documents seen | 2,030 |
| Documents parsed | 2,005 |
| Documents failed | 25 |
| Parse failure rate | 1.23% of seen documents |
| Records written | 1,841 |
| Records skipped | 164 |
| Write skip rate | 8.18% |
| Throughput | 1,443.6 parsed docs/s |

Failed documents equal the 25 unknown-root stubs. Truncated XML was recovered by `lxml` `recover=True` rather than aborting the file, which is the production `skip_errors` behavior.

## Replay pass (cross-run SQLite dedup)

The unique file was parsed a second time into the same `patents.db`.

| Metric | Value |
| --- | ---: |
| Documents parsed | 2,000 |
| Records written | 0 |
| Records skipped | 2,000 |
| All skipped | true |

Identity is `(document_type, patent_grant_id, application_number, publication_date)` hashed as `record_key`. Interrupted backfills can be restarted without duplicating SQLite rows. JSONL is append-only per process; global JSONL dedup happens at Parquet export.

## Scaling note (do not ignore)

Fixture records are short. Unique JSONL averaged **1,947.5 bytes/row**. The published snapshot averages **147,368 bytes/row** of JSONL, about **76×** more text.

If parse time scales with text volume on this hardware, a single-process estimate for production documents is on the order of **~19 docs/s**, or roughly **3.6 days** of CPU time to re-parse 5.93 million full-text records, plus download and I/O. Weekly incremental ingest of ~6,000–10,000 new documents would then be **minutes**, not months.

These two numbers answer different questions:

- **1,465 docs/s** is the measured, reproducible parser overhead on small documents.
- **~19 docs/s** is a size-adjusted planning figure for full-text USPTO records on this 4-vCPU box.

A buyer with more cores can shard by weekly ZIP. The parser is constant-memory per document.

Raw JSON: [metrics/ingestion_benchmark.json](metrics/ingestion_benchmark.json).
