# Compressed and uncompressed corpus sizes

Measured 2026-09-21 from the published Hub tree and from Parquet footers of all 44 shards. JSONL input size is the `source_bytes` field in the snapshot's `release_manifest.json`.

## Three layers of "size"

| Layer | Bytes | GB (decimal) | GiB | What it is |
| --- | ---: | ---: | ---: | --- |
| JSONL ingest artifact | 873,811,406,212 | 873.81 | 813.80 | Uncompressed UTF-8 JSON Lines that fed the exporter |
| Decoded Parquet pages | 970,249,571,241 | 970.25 | 903.61 | Uncompressed column pages inside the 44 shards (includes alias duplicates) |
| Published Parquet files | 211,407,133,718 | 211.41 | 196.89 | Zstandard + dictionary files on the Hub |
| Hub sidecars | 21,794 | 0.00 | 0.00 | README, data-rights notice, release manifest, gitattributes |

JSONL → Parquet **file** ratio: **0.2419** (24.19% of the JSONL remains on disk).
Parquet page compression: **0.2177** (column pages shrink to 21.77%).

Decoded pages exceed JSONL because the Arrow schema stores canonical fields **and** HUPD aliases (`description_text` and `full_description` are each 402.79 GB uncompressed).

## Per unique record (5,929,464 rows)

| | Bytes / row |
| --- | ---: |
| JSONL input | 147,368 |
| Published Parquet file | 35,654 |
| Decoded Parquet pages | 163,632 |

## Split inventory

| Split | Rows | Shards | Parquet file bytes | Decoded page bytes |
| --- | ---: | ---: | ---: | ---: |
| train (publication year < 2025) | 4,676,062 | 34 | 168,726,566,782 | 769,123,310,269 |
| validation (2025) | 772,091 | 6 | 26,272,956,667 | 123,685,149,677 |
| test (2026+) | 481,311 | 4 | 16,407,610,269 | 77,441,111,295 |
| unspecified | 0 | 0 | 0 | 0 |
| **total** | **5,929,464** | **44** | **211,407,133,718** | **970,249,571,241** |

Test shards: **4**. Validation: **6**. Train: **34**.

## Raw USPTO ZIP archives

Project documentation describes official weekly grant and application ZIP dumps **on the order of 1.6 TB** before the pipeline deletes them. That figure was **not re-weighed in this environment**: completed archives are not retained, and `bulkdata.uspto.gov` did not resolve from the measurement host. Buyers should budget:

- Transient raw ZIP disk for one or more weeks (hundreds of MB to a few GB each)
- Persistent JSONL/SQLite if they keep local ingest artifacts (~0.9 TB JSONL at current snapshot scale)
- Persistent Parquet (~0.21 TB) for the publishable snapshot
- Working headroom: the exporter requires decoded-output × 1.2, minimum 2 GB free

## Buyer disk planning (snapshot consume-only)

To load the Hub snapshot without re-ingesting XML:

- **~212 GB** to hold the 44 Parquet shards
- Plus client cache if `datasets` downloads rather than streams
- Streaming (`load_dataset(..., streaming=True)`) avoids the full download

Raw JSON: [metrics/corpus_inventory.json](metrics/corpus_inventory.json), [metrics/parquet_inventory.json](metrics/parquet_inventory.json).
