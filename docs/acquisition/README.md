# PatentPulse acquisition data room

Immutable diligence package for evaluating an acquisition or licensing of
**PatentPulse** — the USPTO weekly-dump ingestion pipeline and the published
`theworker02/patentpulse` corpus.

| Document | Contents |
| --- | --- |
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Buyer one-pager: what transfers, why it saves months |
| [QUALITY_METRICS.md](QUALITY_METRICS.md) | Field fill rates, text length distributions, split integrity |
| [CORPUS_SIZES.md](CORPUS_SIZES.md) | Compressed / uncompressed sizes with methodology |
| [DEDUP_AND_ERROR_RATES.md](DEDUP_AND_ERROR_RATES.md) | Release dedup yield and malformed-row rates |
| [INGESTION_BENCHMARK.md](INGESTION_BENCHMARK.md) | Reproducible parse throughput numbers |
| [BUYER_DEPLOYMENT.md](BUYER_DEPLOYMENT.md) | End-to-end deploy, resume, and re-export procedure |
| [metrics/](metrics/) | Machine-readable JSON from the measurement scripts |
| [outreach/](outreach/) | Target acquirer map and pitch copy |

## Reproduce the hard metrics

```bash
pip install -r requirements.txt
pip install huggingface_hub   # metrics script only

python scripts/benchmark_ingestion.py \
  --docs 2000 \
  --output docs/acquisition/metrics/ingestion_benchmark.json

python scripts/compute_acquisition_metrics.py \
  --output docs/acquisition/metrics/acquisition_metrics.json
```

Unit tests (pipeline contract):

```bash
python -m pytest tests -q
```

## Snapshot identity (published Hub release)

| Property | Value |
| --- | --- |
| Hub dataset | [`theworker02/patentpulse`](https://huggingface.co/datasets/theworker02/patentpulse) |
| Release created | `2026-08-28T03:13:23+00:00` |
| Unique records | **5,929,464** |
| Canonical digest | `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944` |
| Temporal splits | train 4,676,062 · validation 772,091 · test 481,311 |

## What a buyer receives

1. **MIT-licensed pipeline** (`patentpulse/`) — stream parse, clean, SQLite/JSONL writers, resumable ODP sync, guarded Parquet exporter.
2. **Published Parquet snapshot** — Zstandard shards + `release_manifest.json` with content digest.
3. **Provenance model** — per-week source URL, SHA-256, parse counts in `data/manifest.json` (local; regenerated on sync).
4. **This data room** — measured sizes, quality sample, dedup/error rates, deployment runbook, outreach materials.

Raw USPTO text remains subject to USPTO terms; see [DATA_LICENSE.md](../../DATA_LICENSE.md).
