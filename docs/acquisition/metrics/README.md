# Regenerating measurement artifacts

```bash
python -m pip install -r requirements.txt
python -m patentpulse.metrics --output docs/acquisition/metrics --documents 2000
```

`--skip-hub` reuses `hf_release_manifest.json` already in this folder (offline JSONL math only; Parquet footers are not refreshed).

`work/` is gitignored scratch for the local ingest benchmark.
