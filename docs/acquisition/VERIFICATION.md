# Freeze verification — Acquisition Release 1.0

Recorded on the measurement host after the Acquisition Release 1.0 packet landed.

| Check | Result |
| --- | --- |
| `python -m pytest tests -q` | **24 passed** |
| `python -m patentpulse.metrics --documents 2000` | collected_at `2026-09-21T02:11:08+00:00`; unique_records **5,929,464**; parquet **211,407,133,718** bytes; ingest **~1,453 docs/s** unique-pass |
| `python scripts/buyer_demo.py` | **PASS** in **0.09 s** wall (fixture path) |
| `python -m patentpulse.coverage --from-date 2018-01-01 --to-date 2026-09-21` | calendar envelope **910** expected archives; this clone has empty operator manifest → **910** missing (see CORPUS_FINISH.md) |

Canonical digest unchanged: `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944`.
