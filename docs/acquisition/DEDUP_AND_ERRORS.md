# Deduplication and error rates

## Published snapshot (JSONL → Parquet export)

Identity: `sha256(document_type, patent_grant_id, application_number, publication_date)`.

| Quantity | Count | Rate |
| --- | ---: | ---: |
| JSONL rows attempted | 6,500,364 | 100% of export input lines with content |
| Valid JSON objects | 6,500,178 | 99.9971% |
| Malformed rows skipped | **186** | **0.00286%** |
| Duplicates skipped | **570,714** | **8.78% of valid JSON** |
| Unique records written | **5,929,464** | **91.22% of valid JSON** |

Check: `6,500,178 - 570,714 = 5,929,464`. The identity equation holds.

### Malformed JSON by parser message

| Error | Rows |
| --- | ---: |
| Expecting value | 174 |
| Extra data | 9 |
| Expecting ',' delimiter | 2 |
| Invalid UTF-8: invalid start byte | 1 |
| **Total** | **186** |

These rows were skipped only because the export was run with `--skip-invalid-json`. The default exporter still refuses a dirty JSONL file. Line numbers are in [metrics/hf_release_manifest.json](metrics/hf_release_manifest.json).

The 186 failures are concentrated in two JSONL regions (around lines 2.63M–2.65M and 5.07M–5.20M), which is the signature of a torn write during an interrupted append, not of systematically bad USPTO XML.

## Local ingest (XML → SQLite)

SQLite uses `UNIQUE (patent_grant_id, application_number, publication_date)` plus `record_key`. JSONL writers suppress duplicates only within a process. That is why export-time global dedup removed 570,714 rows: append-only JSONL from retries and overlapping runs.

Measured on the 2026-09-21 mixed fixture (2,000 patents, 8% duplicate identities, 25 unknown roots, 5 truncated documents):

| Event | Count | Rate |
| --- | ---: | ---: |
| Unknown-root / unparseable documents | 25 | 1.23% of 2,030 seen |
| Duplicate identities skipped at write | 164 | 8.18% of write attempts |
| Second-pass replay writes | 0 | 100% skip |

Sequence-listing and other non-patent companion XML is counted as `documents_failed` and is **not** written. A completed weekly manifest entry therefore means "this ZIP finished," not "every XML block was a patent."

## XML ingest failures in the published snapshot

The Hub package does **not** include the local `data/manifest.json` (workstation paths, per-week parse-failure counts). Buyers who take the pipeline inherit per-file `records_failed` once they run `ingest sync`. Buyers who only take the Parquet snapshot should use the JSONL export rates above.

## What "error" does not include

- Sparse abstracts on design/plant patents
- CPC labels the USPTO omitted
- Alias columns that duplicate canonical text
- Empty `unspecified` split (a card bug, not row loss)

Raw JSON: [metrics/dedup_and_errors.json](metrics/dedup_and_errors.json).
