# Buyer quick start — 15-minute evaluation

A short path for acquisition diligence: prove the pipeline works locally, inspect a tiny corpus, and optionally sample the published Hub snapshot. For the scripted end-to-end demo (&lt;10 minutes), prefer [acquisition/BUYER_DEMO.md](acquisition/BUYER_DEMO.md).

## Minute 0–3: install and tests

```bash
cd patentpulse   # or your clone path
python -m pip install -r requirements.txt
python -m pytest tests -q
```

Expected: green suite (includes `tests/test_peek.py`). No USPTO API key required.

## Minute 3–8: local demo corpus + peek

```bash
python scripts/buyer_demo.py --keep-dir /tmp/patentpulse-demo
```

Then point peek at the demo database (path printed by the script, typically under the keep-dir):

```bash
python -m patentpulse.peek --db /tmp/patentpulse-demo/data/processed/patents.db stats
python -m patentpulse.peek --db /tmp/patentpulse-demo/data/processed/patents.db search "sensor" --limit 5
python -m patentpulse.peek --db /tmp/patentpulse-demo/data/processed/patents.db get 10000000
```

If there is no local DB yet:

```bash
python -m patentpulse.peek stats
# → tells you to run ingest or use the Hugging Face dataset
```

## Minute 8–12: published snapshot (optional, streaming)

```python
from datasets import load_dataset

stream = load_dataset("theworker02/patentpulse", split="train", streaming=True)
row = next(iter(stream))
print(row["invention_title"], row.get("publication_date"))
```

Full download is ~212 GB compressed Parquet — do not start a full pull in a 15-minute window. Streaming is enough to verify schema and sample quality. See [HUB_VIEWER_FIX.md](acquisition/HUB_VIEWER_FIX.md) if the Hub dataset viewer shows an empty `unspecified` split.

## Minute 12–15: read the packet

1. Root brief: [ACQUISITION.md](../ACQUISITION.md)
2. Numbers: [acquisition/EXECUTIVE_SUMMARY.md](acquisition/EXECUTIVE_SUMMARY.md)
3. What transfers: [acquisition/ASSET_SCHEDULE.md](acquisition/ASSET_SCHEDULE.md)
4. Deploy paths: [acquisition/BUYER_DEPLOYMENT.md](acquisition/BUYER_DEPLOYMENT.md)

## Acceptance checklist

| Check | Pass if |
| --- | --- |
| Tests | `pytest` exits 0 |
| Peek stats | Non-zero row counts on demo DB |
| Peek search / get | Returns title/abstract or JSON record |
| Hub stream (optional) | One row with `invention_title` |

## Contact

GitHub [@theworker02](https://github.com/theworker02) — acquisition / IP-transfer discussions only after internal qualification. **No asking price** in outbound materials.
