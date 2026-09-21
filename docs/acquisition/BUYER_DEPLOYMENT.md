# Buyer deployment procedure

Two supported ways to take PatentPulse. Path A is hours. Path B is a resumable backfill, not a greenfield parser project.

Python 3.10+ is required. GPU is not.

## Path A — consume the published snapshot

Use this when the product need is text, CPC, citations, and temporal splits.

1. Confirm disk: **212 GB** if you materialize all 44 Parquet shards; streaming needs much less.
2. Install `datasets` and `pyarrow` in the buyer's environment.
3. Apply the Hub card fix in [HUB_VIEWER_FIX.md](HUB_VIEWER_FIX.md) if the Dataset Viewer still lists an empty `unspecified` split. Loading via `data_files` still works without the viewer.
4. Load:

```python
from datasets import load_dataset

ds = load_dataset("theworker02/patentpulse")
print(ds)
print(ds["train"].features)

stream = load_dataset("theworker02/patentpulse", split="train", streaming=True)
row = next(iter(stream))
assert row["title"] == row["invention_title"]
```

5. Verify identity against [metrics/dedup_and_errors.json](metrics/dedup_and_errors.json):
   - train 4,676,062
   - validation 772,091
   - test 481,311
   - total 5,929,464
   - canonical digest `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944`
6. Keep `DATA_LICENSE.md` and `release_manifest.json` with any internal copy.
7. Do not treat missing bibliographic extras as proof they were absent from the USPTO XML. See [QUALITY_METRICS.md](QUALITY_METRICS.md).

Acceptance: splits match, aliases match on a sample, `source_file` contains only a filename.

## Path B — own the pipeline and rebuild or extend

Use this to continue the 2018–2026 backfill, re-extract historical weeks for inventor/examiner fields, or change the schema.

### B1. Get the code

```bash
git clone https://github.com/theworker02/patentpulse.git
cd patentpulse
python -m pip install -r requirements.txt
python -m pytest tests -q
```

Expected: the current test suite passes (21 tests at the time of this packet).

### B2. Reproduce this packet's measurements

```bash
python -m patentpulse.metrics --output docs/acquisition/metrics --documents 2000
```

Expected: unique-pass `documents_failed == 0`, replay pass writes 0 rows, Hub footer inventory returns 44 shards if the measurement host can reach `huggingface.co`.

### B3. Local smoke ingest (no USPTO key)

```bash
python -m patentpulse.ingest init
python -m patentpulse.ingest run --format both
python -m patentpulse.ingest status
python examples/inspect_record.py
```

Expected: the seeded fixture parses into `data/processed/patents.db` and `patents.jsonl`.

### B4. Official weekly backfill

1. Register a USPTO Open Data Portal key at https://data.uspto.gov/apis/getting-started
2. Export it only in the process environment. Do not commit it.

```bash
export USPTO_API_KEY="..."
python -m patentpulse.ingest sync --source both --format both
```

Behavior the buyer should rely on:

- Completed weeks in `data/manifest.json` are skipped.
- Stale `running` rows are recovered.
- A process lock prevents overlapping syncs.
- ZIP size is checked against the catalog.
- Archives are deleted after a successful ingest unless `--keep-raw`.
- Grant and application weeks interleave when `--source both`.

### B5. Publish an internal snapshot

```bash
python -m patentpulse.hf_release export \
  --input data/processed/patents.jsonl \
  --output /data/releases/patentpulse-internal \
  --skip-invalid-json

python -m patentpulse.hf_release validate --release /data/releases/patentpulse-internal
```

The exporter refuses incomplete ingest manifests and insufficient disk. It will not list empty splits in the generated Hub card (fix landed with this packet).

## Rights and operations

- Code and original docs: MIT ([LICENSE](../../LICENSE)).
- Snapshot reuse: [DATA_LICENSE.md](../../DATA_LICENSE.md) and USPTO terms. Label Hub copies `other`.
- Do not upload `patents.db`, `patents.jsonl`, raw ZIPs, or `data/manifest.json` to a public dataset repo.
- Pause scheduled ingest while cutting a snapshot ([docs/RELEASING.md](../RELEASING.md)).

## Suggested acceptance tests for an acquired deployment

| Test | Command or check |
| --- | --- |
| Unit | `python -m pytest tests -q` |
| Metrics | `python -m patentpulse.metrics --documents 200` |
| Fixture ingest | `ingest run` writes ≥2 rows |
| Dedup | second parse of the same file writes 0 SQLite rows |
| Snapshot identity | record counts and digest match the Hub manifest |
| Path hygiene | `source_file` has no `/`, `\`, or drive letters |
| Card | generated README has no `data/unspecified/*.parquet` glob unless that split has rows |
