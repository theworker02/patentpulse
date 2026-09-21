# Buyer deployment procedure

Reproducible path from zero to a running PatentPulse corpus and optional Hub
re-export. Validated command shapes match the repository README and
`docs/HF_RELEASE.md`.

## 0. Prerequisites

| Requirement | Notes |
| --- | --- |
| Python 3.10+ | 3.12 verified in this data room |
| Disk | ≥ 220 GB to pull Hub Parquet; ≥ 1 TB recommended for JSONL + export headroom; multi-TB if `--keep-raw` |
| USPTO ODP API key | Required only for live `ingest sync` |
| Optional HF token | Only for private mirrors / upload |

```bash
git clone https://github.com/theworker02/patentpulse.git
cd patentpulse
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests -q
```

## 1. Fastest path — use the published snapshot (no ingest)

```python
from datasets import load_dataset

ds = load_dataset("theworker02/patentpulse")
stream = load_dataset("theworker02/patentpulse", split="train", streaming=True)
print(next(iter(stream))["invention_title"])
```

Verify digest:

```bash
# After downloading release_manifest.json from the Hub dataset root
python - <<'PY'
import json
m = json.load(open("release_manifest.json"))
assert m["records_written"] == 5929464
assert m["canonical_sha256"] == "42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944"
print("release identity OK")
PY
```

## 2. Local workspace bootstrap

```bash
python -m patentpulse.ingest status
# Creates data/ layout + empty manifest on first use when sync/run is invoked
```

Layout:

```text
data/
├── manifest.json
├── raw/grants/
├── raw/applications/
└── processed/
    ├── patents.db
    └── patents.jsonl
```

## 3. Smoke ingest (offline fixture)

```bash
python -m patentpulse.parse \
  --input tests/fixtures/sample_bulk.xml \
  --output data/processed/patents.db \
  --format both

python -m patentpulse.ingest status
```

Expect two grants in SQLite/JSONL with inventors, CPC, and citations populated
from the fixture (current extractor).

## 4. Continuous official backfill

```bash
export USPTO_API_KEY="..."   # PowerShell: $env:USPTO_API_KEY = "..."

# Resume both product families; completed weeks are skipped
python -m patentpulse.ingest sync --source both --format both

# Or one family
python -m patentpulse.ingest sync --source grant --format both
python -m patentpulse.ingest sync --source application --format both
```

Operational guarantees:

- Atomic manifest writes; stale `running` recovery; process lock
- Download size validation before commit
- Archive deleted after successful ingest unless `--keep-raw`
- Rate-limit / transient error retries (`--max-fetch-errors`)

Monitor:

```bash
python -m patentpulse.ingest status
```

## 5. Ingest already-downloaded archives

```bash
# Place ZIPs under data/raw/grants or data/raw/applications
python -m patentpulse.ingest run --format both
```

## 6. Build an immutable Parquet release (buyer mirror)

Do **not** upload raw JSONL, SQLite, or the local manifest.

```bash
# Smoke export
python -m patentpulse.hf_release export \
  --input data/processed/patents.jsonl \
  --output /data/releases/patentpulse-smoke \
  --max-records 10000

python -m patentpulse.hf_release validate --release /data/releases/patentpulse-smoke

# Full export (requires large free volume; exporter enforces headroom)
python -m patentpulse.hf_release export \
  --input data/processed/patents.jsonl \
  --output /data/releases/patentpulse-vnext

python -m patentpulse.hf_release validate --release /data/releases/patentpulse-vnext
```

Upload (explicit, separate step):

```bash
hf upload <namespace>/patentpulse /data/releases/patentpulse-vnext --type dataset
```

## 7. Production checklist

- [ ] `pytest` green on the deploy image
- [ ] Secrets only in env / secret manager (`USPTO_API_KEY`, optional `HF_TOKEN`)
- [ ] Dedicated volume for `data/processed` and release output
- [ ] Cron/systemd timer for `ingest sync --source both --format both`
- [ ] Alert on manifest `failed` entries and lock-file age
- [ ] Retain `manifest.json` across regenerations
- [ ] Re-run `scripts/compute_acquisition_metrics.py` after cutting a new release
- [ ] Legal review of [DATA_LICENSE.md](../../DATA_LICENSE.md) for the buyer’s jurisdiction

## 8. Recovery drills

| Failure | Action |
| --- | --- |
| Crash mid-week | Re-run `sync`; completed files skip; in-progress recovered |
| Corrupt download | Manifest marks failed; delete partial raw file; sync retries |
| Overlapping jobs | Lock raises; stop the duplicate process |
| Incomplete manifest at export | `hf_release export` refuses until sources are complete |

## 9. Estimated engineering time saved

For a team that does not already own a USPTO weekly XML platform:

| If building in-house | Typical scope |
| --- | --- |
| ODP auth, catalog, checksummed download | weeks |
| Concatenated XML streaming + schema drift | weeks |
| Cleaning, CPC/claims/description normalization | weeks |
| Resumable store + dedup + release packaging | weeks |
| **PatentPulse transfer** | days to wire secrets, storage, and product adapters |

Exact calendar time varies; the technical surface area above is what this
repository already closes.
