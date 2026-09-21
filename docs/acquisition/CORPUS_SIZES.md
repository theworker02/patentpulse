# Corpus sizes (compressed and uncompressed)

All figures refer to the published Hub dataset unless noted. Measured
2026-09-21 via `scripts/compute_acquisition_metrics.py`.

## Summary table

| Representation | Bytes | Decimal GB | GiB |
| --- | --- | --- | --- |
| **Published Parquet on Hub (Zstd, 44 files + metadata)** | 211,407,155,512 | **211.407** | **196.888** |
| **Source JSONL used for the release (`source_bytes`)** | 873,811,406,212 | **873.811** | 813.9 |
| **Estimated Parquet uncompressed** (footer extrapolation) | 966,691,768,670 | **966.692** | **900.302** |
| README order-of-magnitude raw USPTO archives (project claim) | — | ~1,600 | — |

## Compression ratios

| Comparison | Ratio |
| --- | --- |
| Hub Parquet ÷ JSONL source | **0.2419** (~4.1× smaller) |
| Hub Parquet ÷ estimated Parquet uncompressed | **0.2187** (~4.6×) |
| Per-shard footer compressed ÷ uncompressed (train/val/test samples) | 0.209–0.214 |

The exporter’s planning constant `DEFAULT_EXPECTED_COMPRESSION_RATIO = 0.25`
in `patentpulse/hf_release.py` matches measured Hub-vs-JSONL compression
within ~1 percentage point.

## Shard sample footers

| Shard | Rows | Uncompressed | Compressed (footer) | Ratio |
| --- | --- | --- | --- | --- |
| `data/train/part-00000.parquet` | 148,710 | 23.403 GB | 5.010 GB | 0.2141 |
| `data/validation/part-00005.parquet` | 34,084 | 5.835 GB | 1.228 GB | 0.2105 |
| `data/test/part-00003.parquet` | 36,933 | 6.585 GB | 1.374 GB | 0.2087 |

Average uncompressed **~163,032 bytes/row** in the sample; extrapolated across
5,929,464 unique rows → ~966.7 GB uncompressed Parquet column data.

## Buyer storage planning

| Stage | Rough capacity |
| --- | --- |
| Hub download (Parquet only) | ≥ **220 GB** free |
| Local JSONL rebuild from full backfill | ≥ **900 GB** free |
| Full Parquet re-export working set | JSONL + ~1.2× projected output (exporter enforces headroom) |
| Optional keep-raw USPTO ZIPs | multi-TB if retained; default sync deletes after success |

## Methodology

1. **Hub compressed:** sum of file sizes from `HfApi.list_repo_tree(..., recursive=True)`.
2. **JSONL uncompressed:** `source_bytes` in Hub `release_manifest.json`.
3. **Parquet uncompressed estimate:** sum of
   `ColumnChunk.total_uncompressed_size` across all row groups in three
   representative shards, divide by rows, multiply by `records_written`.

Machine-readable copy: [metrics/acquisition_metrics.json](metrics/acquisition_metrics.json).
