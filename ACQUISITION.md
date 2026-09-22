# Acquisition Brief â€” Full corpus with temporal splits

**Date:** 2026-09-22  
**Repository:** https://github.com/theworker02/patentpulse  
**Default branch:** `main`  
**Primary language:** Python  
**Status:** Diligence briefing only. **No acquisition has occurred** by virtue of this file.  
**License:** Proprietary â€” sale, written commercial license, or completed asset transfer required (see root `LICENSE`).  
**Valuation:** Not stated.  
**Contact:** GitHub [@theworker02](https://github.com/theworker02) Â· [thanks.dev/u/gh/theworker02](https://thanks.dev/u/gh/theworker02)

> Cloning or forking this repository does **not** grant production, redistribution, SaaS, OEM, or commercial rights.

---

## 1. Executive thesis

<img src="assets/patentpulse-logo.svg" alt="PatentPulse" width="440" /> <p><strong>A continuously growing, provenance-preserving corpus of USPTO patent grants and published applications.</strong><br/> Official weekly XML dumps are streamed, parsed in constant memory, cleaned, and normalized into SQLite, JSON Lines, and a publishable Parquet snapshot.</p>

**Why a buyer cares:** Full corpus with temporal splits packages transferable product IP â€” source, docs, in-repo brand assets, and a diligence room under `docs/acquisition/` â€” under a clear proprietary posture so diligence can proceed without mistaking the repo for open source.

---

## 2. Product snapshot

| Item | Detail |
|------|--------|
| Product | Full corpus with temporal splits |
| Repo | `theworker02/patentpulse` |
| Language | Python |
| Open source? | **No** â€” proprietary |
| Rightsholder | theworker02 |
| Diligence pack | `docs/acquisition/` |

### Capability highlights (from current materials)

- [What PatentPulse is](#what-patentpulse-is)
- [Dataset at a glance](#dataset-at-a-glance)
- [Use the published dataset](#use-the-published-dataset)
- [Why weekly dumps matter](#why-weekly-dumps-matter)
- [Quick start](#quick-start)
- [Continue the official backfill](#continue-the-official-backfill)
- [Outputs](#outputs)
- [Building a Hugging Face release](#hugging-face-release)
- [Architecture](#architecture)
- [Command reference](#command-reference)
- [Quality and validation](#quality-and-validation)
- [Acquisition data room](#acquisition-data-room)

---

## 3. Problem / opportunity

Teams evaluating Full corpus with temporal splits typically need either (a) a commercial right to run or embed it, or (b) outright ownership of the Product IP for strategic build-out. Public GitHub visibility without a proprietary license creates false assumptions about free production use. This brief and the linked data room make the commercial path explicit.

---

## 4. What ships today

Honest maturity: treat repository contents, README claims, tests, and release tags as the source of truth. Do not assume production customers, ARR, filed patents, or SLAs unless separately evidenced in diligence.

Typical transferable surfaces:

- Source tree and build/test scripts present in-repo
- Documentation and design notes
- Acquisition / diligence markdown under `docs/acquisition/`
- Branding assets committed to the repository (if any)

---

## 5. Demo / evaluation path (buyer)

Minimal path (no secrets required unless README says otherwise):

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

Extended evaluation: `docs/acquisition/BUYER_EVALUATION.md`. Written NDA / evaluation grants may be required for private materials.

---

## 6. What a transaction typically includes

Subject to definitive schedules:

| Included (typical) | Excluded (typical) |
|--------------------|--------------------|
| Repo materials + asserted original IP | Seller personal accounts / unrelated repos |
| Docs + diligence room at closing | Third-party dependency source under separate licenses |
| In-repo brand marks as assigned | Secrets without rotation plan |
| Know-how captured in docs | Fabricated revenue, user, or adoption metrics |

---

## 7. Suggested deal structures

| Structure | When it fits |
|-----------|--------------|
| Non-exclusive commercial license | Deploy/run under seat or environment terms |
| Exclusive field-of-use license | Buyer wants exclusivity; seller may retain entity |
| Asset / IP assignment | Buyer wants ownership of Materials outright |
| OEM / redistribution | Separate agreement â€” not implied here |

Commercial terms (price, earnouts, escrow) are negotiated under NDA with counsel.

---

## 8. Buyer diligence checklist

- [ ] Confirm Rightsholder identity and authority to sell/license
- [ ] Inventory Materials (`docs/acquisition/ASSET_INVENTORY.md`)
- [ ] Review IP posture (`IP_PROVENANCE.md`) and dependencies (`DEPENDENCY_INVENTORY.md`)
- [ ] Run evaluation script (`BUYER_EVALUATION.md`)
- [ ] Review risks (`RISK_REGISTER.md`)
- [ ] Agree transfer scope (`TRANSFER_MANIFEST.md`) and handoff (`HANDOFF_CHECKLIST.md`)
- [ ] Supersede root `LICENSE` at closing via definitive agreement

---

## 9. Related documents

| Document | Purpose |
|----------|---------|
| `LICENSE` | Proprietary â€” no default grant |
| `docs/acquisition/README.md` | Data-room index |
| `docs/acquisition/EXECUTIVE_SUMMARY.md` | One-page thesis |
| `README.md` | Product overview |
| `SECURITY.md` | Vulnerability reporting |
| `COMMERCIAL.md` | Licensing contact path |
| `.github/FUNDING.yml` | Sponsors / thanks.dev |

---

## 10. Disclaimer

This package is informational and **does not** create a binding offer, grant of rights, or investment advice. Engage counsel for any transaction.

---

*Document version: 2.0.0 / 2026-09-22 Â· Classification: acquisition briefing*
