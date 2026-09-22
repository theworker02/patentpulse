# PatentPulse acquisition data room

Buyer packet for **PatentPulse Acquisition Release 1.0** (`theworker02/patentpulse`): measured corpus quality, ingestion throughput, compressed and uncompressed sizes, deduplication and error rates, a reproducible deployment procedure, a &lt;10-minute buyer demo, a formal asset schedule, and the companies for whom an acquisition replaces months of USPTO data engineering.

Numbers in `metrics/` were produced on 2026-09-21 by:

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m patentpulse.metrics --output docs/acquisition/metrics --documents 2000
python scripts/buyer_demo.py
```

Re-run those commands to refresh the JSON and demo timings. Do not treat marketing copy elsewhere in the repository as the source of truth when it disagrees with these artifacts.

## Contents

| Document | What a buyer gets |
| --- | --- |
| [ACQUISITION_RELEASE.md](ACQUISITION_RELEASE.md) | **Freeze identity** — records, shards, years, digest, verification |
| [VERIFICATION.md](VERIFICATION.md) | Commands run at freeze + pass/fail |
| [TEASER.md](TEASER.md) | One-page acquisition teaser (numbers first, no asking price) |
| [ASSET_SCHEDULE.md](ASSET_SCHEDULE.md) | What transfers vs USPTO material vs OSS dependencies |
| [CORPUS_FINISH.md](CORPUS_FINISH.md) | Remaining weekly coverage, storage/compute, automated finish |
| [BUYER_DEMO.md](BUYER_DEMO.md) | &lt;10 min evaluation: source → ingest → query → Parquet |
| [../BUYER_QUICKSTART.md](../BUYER_QUICKSTART.md) | 15-minute evaluator path (peek + Hub stream) |
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Headline metrics and the acquisition thesis |
| [QUALITY_METRICS.md](QUALITY_METRICS.md) | Field fill rates over all 5,929,464 published rows |
| [INGESTION_BENCHMARK.md](INGESTION_BENCHMARK.md) | Measured docs/sec, replay dedup, hardware |
| [CORPUS_SIZE.md](CORPUS_SIZE.md) | JSONL, Parquet file, and decoded page sizes |
| [DEDUP_AND_ERRORS.md](DEDUP_AND_ERRORS.md) | Duplicate yield, malformed JSON, parse failures |
| [BUYER_DEPLOYMENT.md](BUYER_DEPLOYMENT.md) | Consume-the-snapshot vs rebuild-the-pipeline |
| [BUILD_VS_BUY.md](BUILD_VS_BUY.md) | What an internal team otherwise has to build |
| [TARGET_ACQUIRERS.md](TARGET_ACQUIRERS.md) | First 25 strategic prospects + Wave 1 |
| [OUTREACH.md](OUTREACH.md) | Asset-transaction pitch (no asking price) + contact log |
| [HUB_VIEWER_FIX.md](HUB_VIEWER_FIX.md) | Empty `unspecified` split that currently breaks the Hub viewer |
| [IP_AUDIT.md](IP_AUDIT.md) | Code vs USPTO text; brand; AI authorship flag |
| [LICENSE_HISTORY.md](LICENSE_HISTORY.md) | Proprietary present; historical grants survivors |
| [TRANSFER_PLAN.md](TRANSFER_PLAN.md) | Close / post-close operational checklist |
| [READINESS_REPORT.md](READINESS_REPORT.md) | Gate statuses without a fake numeric score |
| [TEST_EVIDENCE.md](TEST_EVIDENCE.md) | pytest + buyer demo + CI |
| [SECURITY_POSTURE.md](SECURITY_POSTURE.md) | Local-first trust boundaries |
| [DISCLOSURE_SCHEDULE.md](DISCLOSURE_SCHEDULE.md) | Bibliographic null cluster, Hub viewer, license transition |
| [outreach/](outreach/) | Earlier outreach log and pitch drafts (diligence trail) |
| [metrics/](metrics/) | Machine-readable reports |

Root brief: [`../../ACQUISITION.md`](../../ACQUISITION.md) · Security policy: [`../../SECURITY.md`](../../SECURITY.md)

## Snapshot identity

| Field | Value |
| --- | --- |
| Release | **PatentPulse Acquisition Release 1.0** |
| Dataset | [`theworker02/patentpulse`](https://huggingface.co/datasets/theworker02/patentpulse) |
| Pipeline | [`theworker02/patentpulse`](https://github.com/theworker02/patentpulse) |
| Snapshot created | 2026-08-28T03:13:23+00:00 |
| Canonical digest | `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944` |
| Unique records | 5,929,464 |
| Publication years | 2018–2026 |
| JSONL input | 873,811,406,212 bytes |
| Published Parquet | 211,407,133,718 bytes (**44** shards) |
