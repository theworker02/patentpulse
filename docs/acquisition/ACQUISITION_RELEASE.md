# PatentPulse Acquisition Release 1.0

**Release name:** PatentPulse Acquisition Release 1.0  
**Frozen:** 2026-09-21  
**Pipeline:** [`theworker02/patentpulse`](https://github.com/theworker02/patentpulse)  
**Published snapshot:** [`theworker02/patentpulse`](https://huggingface.co/datasets/theworker02/patentpulse)

This document freezes the acquisition-ready package: code, measured metrics, buyer demo, asset schedule, and corpus-finish procedure. Marketing copy elsewhere must yield to the numbers below when they disagree.

## Snapshot identity (what is included)

| Field | Exact value |
| --- | --- |
| Unique released records | **5,929,464** |
| Publication-year coverage in snapshot | **2018–2026** (train &lt;2025 · validation 2025 · test 2026+) |
| Parquet shards | **44** (train 34 · validation 6 · test 4 · unspecified 0) |
| Split row counts | train **4,676,062** · validation **772,091** · test **481,311** |
| Valid JSONL rows seen before export | 6,500,178 |
| Duplicates removed at export | 570,714 (8.78% of valid JSON) |
| Malformed JSONL quarantined | 186 (0.00286% of attempted rows) |
| Unique yield of valid JSON | 91.22% |
| Uncompressed JSONL input | 873,811,406,212 bytes (873.81 GB) |
| Published Zstd Parquet | 211,407,133,718 bytes (211.41 GB) |
| Decoded Parquet page bytes | 970,249,571,241 bytes (970.25 GB) |
| Snapshot created (UTC) | 2026-08-28T03:13:23+00:00 |
| Canonical digest | `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944` |

These counts are pinned in `metrics/dedup_and_errors.json`, `metrics/corpus_inventory.json`, and the Hub `release_manifest.json`.

## What this freeze is — and is not

**Is:** a production USPTO grants-and-applications ingest/normalize/release plant plus an immutable 5.93M-row Parquet snapshot with provenance, tests, and acquisition diligence materials.

**Is not:** a claim that every USPTO weekly ZIP from 2018-01-01 through freeze date is marked `complete` in the private operator `data/manifest.json`. Publication years 2018–2026 appear in the snapshot; weekly archive completeness is a separate, documented finish job ([CORPUS_FINISH.md](CORPUS_FINISH.md)).

## Verification commands (reproducible)

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m patentpulse.metrics --output docs/acquisition/metrics --documents 2000
python scripts/buyer_demo.py
```

Expected at freeze:

- Full test suite: **24 passed** (includes coverage unit tests)
- Metrics unique-pass: `documents_failed == 0`; replay pass writes **0** new SQLite rows
- Buyer demo: end-to-end sample pipeline completes in **under 10 minutes** (measured **&lt;1 s** wall on the Acquisition Release 1.0 measurement host for the fixture path)

Offline metrics refresh (reuse cached Hub tree):

```bash
python -m patentpulse.metrics --output docs/acquisition/metrics --skip-hub --documents 2000
```

## Packet contents

| Artifact | Path |
| --- | --- |
| One-page teaser | [TEASER.md](TEASER.md) |
| Asset schedule (owned IP vs USPTO vs OSS) | [ASSET_SCHEDULE.md](ASSET_SCHEDULE.md) |
| Corpus remaining + finish automation | [CORPUS_FINISH.md](CORPUS_FINISH.md) |
| Buyer demo (&lt;10 min sample) | [BUYER_DEMO.md](BUYER_DEMO.md) · `scripts/buyer_demo.py` |
| Executive metrics | [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) |
| Machine-readable reports | [metrics/](metrics/) |
| Strategic outreach (no asking price) | [OUTREACH.md](OUTREACH.md) · [TARGET_ACQUIRERS.md](TARGET_ACQUIRERS.md) |

## Commercial posture

Source code in this tree is **source-available proprietary** evaluation software ([LICENSE](../../LICENSE), [COMMERCIAL.md](../../COMMERCIAL.md)). Published USPTO-derived snapshot text remains subject to [DATA_LICENSE.md](../../DATA_LICENSE.md) and USPTO terms. See the asset schedule for the transfer vs non-transfer distinction.

## Tagging recommendation

After this packet lands on the default branch, cut an annotated source tag:

```text
acquisition-release-1.0
```

Point the GitHub release notes at this file, the Hub revision that carries digest `42d3a4ae…4944`, and the verification commands above. Do not attach `patents.db`, `patents.jsonl`, raw ZIPs, or `data/manifest.json` to the GitHub release.
