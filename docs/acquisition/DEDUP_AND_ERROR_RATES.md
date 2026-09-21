# Deduplication and error rates

Figures from Hub `release_manifest.json` for the 2026-08-28 PatentPulse
release. Recompute anytime with
`scripts/compute_acquisition_metrics.py`.

## Release-time global deduplication

The Parquet exporter deduplicates append-only JSONL retries by a stable key
over document type, publication identifier, application number, and
publication date (`patentpulse/hf_release.py`).

| Quantity | Count | Rate vs `records_seen` |
| --- | --- | --- |
| Rows seen in JSONL | 6,500,178 | 100% |
| Duplicates skipped | **570,714** | **8.78%** |
| Unique records written | **5,929,464** | **91.22% yield** |
| Malformed JSON rows skipped | **186** | **0.002861%** |

## Malformed JSON breakdown

| Error prefix | Count |
| --- | --- |
| `Expecting value` | 174 |
| `Extra data` | 9 |
| `Expecting ',' delimiter` | 2 |
| `Invalid UTF-8` | 1 |
| **Total** | **186** |

These rows are skipped; they do not enter shards. Line numbers are retained in
`release_manifest.json` for audit.

## Ingestion-time dedup and parse failures

| Layer | Behavior |
| --- | --- |
| SQLite / JSONL writers | Stable identity hash skips already-written documents across interrupted runs (`patentpulse/schema.py`) |
| Manifest | Per weekly archive: `records_parsed`, `records_written`, `parse` failure counts, SHA-256, source URL |
| Sync | Skips completed archives; recovers stale `running` entries; process lock prevents overlapping ingest |
| Sequence / non-patent companion XML | Skipped; not counted as successful patent records |

A completed manifest entry does **not** imply every XML block in a weekly ZIP
was a patent document.

## Error-rate interpretation for buyers

- **8.78% duplicate removal** is expected for a long-lived append-only JSONL
  that survived retries and partial re-runs — not a measure of USPTO duplicate
  publications.
- **~29 malformed rows per million** input lines is low for multi-hundred-GB
  JSONL and was quarantined at export time.
- Patent-family collapse (application ↔ grant) is **out of scope** for v1;
  buyers needing families should join on application numbers post-ingest.

## Acceptance thresholds (suggested)

| Check | Pass if |
| --- | --- |
| Unique released rows | Equals `sum(records_by_split)` and `records_written` |
| Canonical digest | Matches buyer-copied `release_manifest.json` |
| Invalid JSON rate | ≤ 0.01% of `records_seen` (v1 is ~0.0029%) |
| Duplicate rate | Documented; no hard fail — inspect if ≫ 15% on a fresh single-pass export |
