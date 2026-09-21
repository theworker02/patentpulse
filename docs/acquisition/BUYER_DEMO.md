# Buyer demo — private evaluation package

Not a subscription product and not a giant website. A buyer clones the private evaluation tree (or this repository under the source-available evaluation LICENSE), runs one script, and sees:

**USPTO source → ingestion → normalized record → query/search → Parquet/HF export**

using a small synthetic weekly XML sample. The full multi-terabyte corpus is not required.

## Time budget

| Target | Typical on 4-vCPU / 16 GB (Acquisition Release 1.0 host class) |
| --- | --- |
| **&lt; 10 minutes** | **&lt; 2 minutes** end-to-end |

## Prerequisites

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q   # optional confidence; expected green
```

No USPTO API key. No Hugging Face token. No GPU.

## Run

```bash
python scripts/buyer_demo.py
# or persist artifacts:
python scripts/buyer_demo.py --keep-dir /tmp/patentpulse-demo
```

## What the demo proves

| Step | What you see |
| --- | --- |
| 1. USPTO source | Official-shaped concatenated bulk XML (`tests/fixtures/sample_bulk.xml`) staged as a weekly grant path |
| 2. Ingestion | `patentpulse.ingest` stream-parses into SQLite + JSONL and marks the manifest `complete` |
| 3. Normalized record | One JSONL row with grant id, title, CPC, publication date, document type |
| 4. Query / search | SQL over `patents` ⨝ `patent_cpc` (CPC prefix search) |
| 5. Parquet / HF export | `hf_release` writes Zstd Parquet + `release_manifest.json` and validates |

## Acceptance

- Script exits 0
- Prints `PASS: under 10-minute evaluation budget.`
- Demo workspace contains `data/processed/patents.db`, `patents.jsonl`, and `release/data/**/*.parquet`

## What this is not

- Not a substitute for Path A full Hub download (~212 GB) in [BUYER_DEPLOYMENT.md](BUYER_DEPLOYMENT.md)
- Not a claim about weekly catalog completeness (see [CORPUS_FINISH.md](CORPUS_FINISH.md))
- Not production rights — evaluation only until a commercial license or acquisition closes ([LICENSE](../../LICENSE), [ASSET_SCHEDULE.md](ASSET_SCHEDULE.md))

## After the demo

1. Read [TEASER.md](TEASER.md) and [ACQUISITION_RELEASE.md](ACQUISITION_RELEASE.md)
2. Reproduce metrics: `python -m patentpulse.metrics --documents 200`
3. If relevant to your roadmap, request the private data-room walkthrough and discuss acquisition / IP transfer — **no asking price in outbound materials**
