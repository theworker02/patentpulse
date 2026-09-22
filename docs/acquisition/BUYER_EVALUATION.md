# Buyer evaluation â€” Full corpus with temporal splits

## Goal

In 15â€“45 minutes, verify the Product builds or runs as documented and that proprietary notices are present.

## Steps

1. Confirm root `LICENSE` is proprietary and `ACQUISITION.md` exists.
2. Skim `README.md` install/run claims.
3. Execute:

```
```python
from datasets import load_dataset

# Full corpus with temporal splits
ds = load_dataset("theworker02/patentpulse")
print(ds)  # train / validation / test

# Stream instead of downloading everything
stream = load_dataset("theworker02/patentpulse", split="train", streaming=True)
print(next(iter(stream))["invention_title"])
```
```powershell
python -m patentpulse.ingest status
```
```powershell
pip install -r requirements.txt

# View local corpus coverage and row counts
python -m patentpulse.ingest status

# Inspect a local SQLite corpus (stats / search / get)
python -m patentpulse.peek stats
python -m patentpulse.peek search "machine learning" --limit 10
python -m patentpulse.peek get 10000000

# Parse a downloaded XML or ZIP into SQLite
python -m patentpulse.parse `
  --input data/raw/grants/ipgYYMMDD.zip `
  --output data/processed/patents.db `
  --format sqlite
```
```python
from datasets import load_dataset

ds = load_dataset("theworker02/patentpulse")  # train / validation / test
stream = load_dataset("theworker02/patentpulse", split="train", streaming=True)
print(next(iter(stream))["invention_title"])
```
```powershell
$env:USPTO_API_KEY = "..."
```

4. Run tests if present (`npm test`, `pytest`, `cargo test`, `go test ./...`, etc.).
5. Record README vs observed behavior gaps in workpapers.

## Pass criteria

- [ ] Clone succeeds
- [ ] Documented happy path works **or** failure is explained
- [ ] Minimal path needs no surprise secrets
- [ ] License notices intact

*Updated: 2026-09-22*
