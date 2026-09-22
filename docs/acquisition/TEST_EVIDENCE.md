# Test evidence — PatentPulse

**Date:** 2026-09-21

## Automated tests

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
python scripts/buyer_demo.py
```

CI: [`.github/workflows/test.yml`](../../.github/workflows/test.yml) runs pytest on Python 3.10/3.12 and the buyer demo smoke.

## What tests cover

| Area | Module / script |
| --- | --- |
| Ingest / parse / clean | `tests/test_ingest.py`, `tests/test_pipeline.py` |
| Coverage catalog | `tests/test_coverage.py` |
| HF release builder | `tests/test_hf_release.py` |
| Quality metrics helpers | `tests/test_metrics.py` |
| Local peek CLI | `tests/test_peek.py` (when present) |
| Buyer smoke | `scripts/buyer_demo.py` |

## What tests do not claim

- Full 1.6 TB backfill in CI
- Live USPTO network calls in default CI
- Fabricated Hub download benchmarks inside GitHub Actions
