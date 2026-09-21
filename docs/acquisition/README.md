# PatentPulse acquisition data room

Buyer packet for **PatentPulse** (`theworker02/patentpulse`): measured corpus quality, ingestion throughput, compressed and uncompressed sizes, deduplication and error rates, a reproducible deployment procedure, and the companies for whom an acquisition replaces months of USPTO data engineering.

Numbers in `metrics/` were produced on 2026-09-21 by:

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m patentpulse.metrics --output docs/acquisition/metrics --documents 2000
```

Re-run that command to refresh the JSON. Do not treat marketing copy elsewhere in the repository as the source of truth when it disagrees with these artifacts.

## Contents

| Document | What a buyer gets |
| --- | --- |
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Headline metrics and the acquisition thesis |
| [QUALITY_METRICS.md](QUALITY_METRICS.md) | Field fill rates over all 5,929,464 published rows |
| [INGESTION_BENCHMARK.md](INGESTION_BENCHMARK.md) | Measured docs/sec, replay dedup, hardware |
| [CORPUS_SIZE.md](CORPUS_SIZE.md) | JSONL, Parquet file, and decoded page sizes |
| [DEDUP_AND_ERRORS.md](DEDUP_AND_ERRORS.md) | Duplicate yield, malformed JSON, parse failures |
| [BUYER_DEPLOYMENT.md](BUYER_DEPLOYMENT.md) | Consume-the-snapshot vs rebuild-the-pipeline |
| [BUILD_VS_BUY.md](BUILD_VS_BUY.md) | What an internal team otherwise has to build |
| [TARGET_ACQUIRERS.md](TARGET_ACQUIRERS.md) | Patent, legal-AI, prior-art, scientific, and AI-data buyers |
| [OUTREACH.md](OUTREACH.md) | Pitch text and contact log |
| [HUB_VIEWER_FIX.md](HUB_VIEWER_FIX.md) | Empty `unspecified` split that currently breaks the Hub viewer |
| [outreach/](outreach/) | Earlier outreach log and pitch drafts (kept for diligence trail) |
| [metrics/](metrics/) | Machine-readable reports |

## Snapshot identity

| Field | Value |
| --- | --- |
| Dataset | [`theworker02/patentpulse`](https://huggingface.co/datasets/theworker02/patentpulse) |
| Pipeline | [`theworker02/patentpulse`](https://github.com/theworker02/patentpulse) |
| Snapshot created | 2026-08-28T03:13:23+00:00 |
| Canonical digest | `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944` |
| Unique records | 5,929,464 |
| JSONL input | 873,811,406,212 bytes |
| Published Parquet | 211,407,133,718 bytes (44 shards) |
