<div align="center">

<img src="assets/patentpulse-logo.svg" alt="PatentPulse" width="440" />

<h1>PatentPulse</h1>

<p><strong>A continuously growing, provenance-preserving corpus of USPTO patent grants and published applications.</strong><br/>
Official weekly XML dumps are streamed, parsed in constant memory, cleaned, and normalized into SQLite, JSON Lines, and a publishable Parquet snapshot.</p>

<p>
  <a href="https://github.com/theworker02/patentpulse/releases/latest"><img alt="GitHub release" src="https://img.shields.io/github/v/release/theworker02/patentpulse?sort=semver&label=release&color=4F46E5"></a>
  <a href="https://huggingface.co/datasets/theworker02/patentpulse"><img alt="Hugging Face dataset" src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-dataset-06B6D4"></a>
  <a href="LICENSE"><img alt="License: Proprietary source-available" src="https://img.shields.io/badge/code%20license-Proprietary%20(source--available)-green"></a>
  <a href="DATA_LICENSE.md"><img alt="Data license: other" src="https://img.shields.io/badge/data%20license-other-lightgrey"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="Records" src="https://img.shields.io/badge/records-5.93M-4F46E5">
  <img alt="Coverage" src="https://img.shields.io/badge/coverage-2018%E2%80%932026-06B6D4">
  <img alt="Format" src="https://img.shields.io/badge/format-Parquet%20%7C%20SQLite%20%7C%20JSONL-orange">
</p>

<p>
  <a href="https://huggingface.co/datasets/theworker02/patentpulse"><strong>Dataset on Hugging Face</strong></a> ·
  <a href="ACQUISITION.md">Acquisition brief</a> ·
  <a href="DATASET_CARD.md">Dataset card</a> ·
  <a href="docs/HF_RELEASE.md">Release exporter</a> ·
  <a href="docs/RELEASING.md">Release checklist</a>
</p>

</div>

---

## Table of contents

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
- [Source and licensing](#source-and-licensing)
- [Citation](#citation)
- [Related work](#related-work)

Acquisition evaluators: start at **[ACQUISITION.md](ACQUISITION.md)**.

## What PatentPulse is

PatentPulse is a locally owned, **continuously growing** corpus (on the order of 1.6 TB of raw source archives) of USPTO patent grants and published applications. It downloads official weekly XML dumps, stream-parses them without loading an archive into memory, and writes normalized SQLite and JSON Lines outputs for search, tokenization, embeddings, and model training.

The repository is a **local data pipeline plus a published dataset**, not a Python package on any index. The pipeline lives here on GitHub; the immutable, ready-to-use snapshot lives on the Hugging Face Hub.

## Dataset at a glance

| Property | Value |
| --- | --- |
| Sources | USPTO Patent Grant Full-Text XML (`PTGRXML`) and Patent Application Full-Text XML (`APPXML`) |
| Cadence | Weekly â€” grants on Tuesday; applications on Thursday |
| Records (published snapshot) | 5,929,464 unique records |
| Temporal splits | train 4,676,062 Â· validation 772,091 Â· test 481,311 |
| Publication coverage | 2018–2026 in published snapshot (5.93M records, 44 shards); weekly catalog finish: [docs/acquisition/CORPUS_FINISH.md](docs/acquisition/CORPUS_FINISH.md) |
| Local storage | SQLite + UTF-8 JSON Lines |
| Published format | Zstandard-compressed Parquet shards (44 files) |
| Primary text | Title, abstract, claims, cleaned description |
| Core labels | Document type, publication date, CPC / IPC |
| Backfill coverage | Tracked in `data/manifest.json` |
| Published snapshot | [`theworker02/patentpulse`](https://huggingface.co/datasets/theworker02/patentpulse) on Hugging Face |

## Use the published dataset

The fastest way to use PatentPulse is the immutable Parquet snapshot on the Hugging Face Hub â€” no ingestion or API key required.

```python
from datasets import load_dataset

# Full corpus with temporal splits
ds = load_dataset("theworker02/patentpulse")
print(ds)  # train / validation / test

# Stream instead of downloading everything
stream = load_dataset("theworker02/patentpulse", split="train", streaming=True)
print(next(iter(stream))["invention_title"])
```

Each row carries canonical PatentPulse fields (`abstract_text`, `claims_text`, `description_text`) plus HUPD-compatible aliases (`title`, `abstract`, `claims`, `full_description`, `cpc_labels`). See the [dataset card](DATASET_CARD.md) for the full field contract.

Run the current local inventory (when working from the pipeline):

```powershell
python -m patentpulse.ingest status
```

## Why weekly dumps matter

There is no one complete USPTO full-text archive for this project. The USPTO delivers patents as weekly releases, and every release contains only the patents published or granted in that week. PatentPulse therefore walks the full official catalog, records each completed archive in the manifest, and skips it on later runs.

## Quick start

Requires Python 3.10+.

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

No local database yet? Load the published Hub snapshot (streaming avoids the full ~212 GB download):

```python
from datasets import load_dataset

ds = load_dataset("theworker02/patentpulse")  # train / validation / test
stream = load_dataset("theworker02/patentpulse", split="train", streaming=True)
print(next(iter(stream))["invention_title"])
```

Acquisition evaluators: [ACQUISITION.md](ACQUISITION.md) and the 15-minute path in [docs/BUYER_QUICKSTART.md](docs/BUYER_QUICKSTART.md).

## Continue the official backfill

Create a USPTO Open Data Portal key, then keep it only in your shell environment:

```powershell
$env:USPTO_API_KEY = "..."

# Resume both datasets. Completed weekly files are skipped.
python -m patentpulse.ingest sync --source both --format both
```

Use one source when required:

```powershell
python -m patentpulse.ingest sync --source grant --format both
python -m patentpulse.ingest sync --source application --format both
```

The sync loop retries rate limits and temporary source errors. It deletes an archive after successful ingestion to conserve disk space; use `--keep-raw` to retain archives.

## Outputs

```text
data/
â”œâ”€â”€ manifest.json              # Per-week source inventory and ingestion status
â”œâ”€â”€ raw/                       # Temporary / manually supplied USPTO archives
â””â”€â”€ processed/
    â”œâ”€â”€ patents.db             # Normalized SQLite corpus
    â””â”€â”€ patents.jsonl          # One dataset record per line
```

Generated bulk data is intentionally ignored by Git.

### SQLite

`patents` holds the normalized text and bibliographic fields. `patent_cpc` holds CPC labels separately, supporting queries such as:

```sql
SELECT p.patent_grant_id, p.invention_title, c.cpc_code
FROM patents AS p
JOIN patent_cpc AS c ON c.patent_id = p.id
WHERE c.cpc_code LIKE 'G06F%'
ORDER BY p.publication_date DESC
LIMIT 20;
```

### JSON Lines

`patents.jsonl` is append-only and is intended for batch NLP pipelines. Each row includes canonical PatentPulse names (`abstract_text`, `claims_text`, `description_text`) and Hugging Face / HUPD-compatible aliases (`abstract`, `claims`, `full_description`, `title`, `cpc_labels`) for easier downstream adaptation.

See [DATASET_CARD.md](DATASET_CARD.md) for the field-level contract, recommended splits, known gaps, bias notes, and source attribution.

### Hugging Face release

Do not upload the append-only `patents.jsonl`, SQLite database, raw archives, or
local `data/manifest.json` directly to Hugging Face. Historical JSONL rows can
have different field sets and the local manifest contains workstation paths.

Create a stable, publishable Parquet snapshot with the guarded release command:

```powershell
python -m patentpulse.hf_release export `
  --input data/processed/patents.jsonl `
  --output E:\releases\patentpulse-v1
```

It blocks an incomplete ingestion manifest, canonicalizes all historical rows,
removes local directories from `source_file`, writes date-based Zstandard
Parquet shards, generates a Hugging Face dataset card, and validates the
result. See [docs/HF_RELEASE.md](docs/HF_RELEASE.md) for storage requirements,
the bounded smoke-export command, and the explicit upload step.

## Architecture

```text
USPTO ODP weekly ZIP
        â”‚
        â–¼
stream.py     splits concatenated XML documents
        â”‚
        â–¼
extract.py    normalizes bibliographic and full-text fields
        â”‚
        â–¼
clean.py      removes XML artifacts and repetitive front matter
        â”‚
        â–¼
schema.py     batches SQLite and JSONL writes
        â”‚
        â–¼
manifest.py   makes backfill resumable and auditable
```

## Command reference

All commands are modules under the `patentpulse` package.

| Command | Purpose |
| --- | --- |
| `python -m patentpulse.ingest status` | Show manifest coverage and database row counts |
| `python -m patentpulse.ingest sync --source both --format both` | Download and ingest remaining weekly dumps (resumable) |
| `python -m patentpulse.ingest run --format both` | Ingest any local archives already present under `data/raw/` |
| `python -m patentpulse.parse --input <file> --output <db> --format sqlite` | Parse a single XML/ZIP/TAR/GZIP file |
| `python -m patentpulse.peek stats` | Local SQLite row counts, date range, document-type breakdown |
| `python -m patentpulse.peek search "<query>" [--limit N]` | Keyword search over title and abstract |
| `python -m patentpulse.peek get <grant-or-app-id>` | Fetch one record as JSON |
| `python -m patentpulse.hf_release export --input <jsonl> --output <dir>` | Build a validated, publishable Parquet snapshot |
| `python -m patentpulse.coverage --from-date 2018-01-01` | Report missing weekly archives vs manifest ([CORPUS_FINISH](docs/acquisition/CORPUS_FINISH.md)) |
| `python scripts/buyer_demo.py` | &lt;10 min evaluation: source → ingest → query → Parquet |
| `./scripts/finish_corpus.sh` | Automated Track A finish loop (requires `USPTO_API_KEY`) |

Ingestion is crash-safe and resumable: it uses atomic manifest writes, recovers stale in-progress entries, holds a process lock to prevent overlapping runs, and validates download sizes before committing a file.

## Quality and validation

```powershell
python -m pytest tests -q
```

The test suite verifies concatenated-document splitting, text cleaning, bibliographic/CPC extraction, and SQLite/JSONL output.

## Acquisition data room

Start with the root brief **[ACQUISITION.md](ACQUISITION.md)** (no valuation). Diligence materials live under
[`docs/acquisition/`](docs/acquisition/README.md): freeze identity, one-page
teaser, asset schedule, corpus-finish procedure, &lt;10-minute buyer demo,
measured metrics, and strategic outreach (no asking price). Fifteen-minute
evaluator path: [docs/BUYER_QUICKSTART.md](docs/BUYER_QUICKSTART.md).

```powershell
python -m pytest tests -q
python -m patentpulse.metrics --output docs/acquisition/metrics --documents 2000
python scripts/buyer_demo.py
```

Legacy helpers `scripts/benchmark_ingestion.py` and
`scripts/compute_acquisition_metrics.py` remain for the earlier sampled
reports; prefer the metrics module above for the full measured packet.

### Release notes (Acquisition Release 1.0 polish)

There is no separate `CHANGELOG` file; version identity is
[VERSION](VERSION) (`PatentPulse Acquisition Release 1.0`). This polish adds
root `ACQUISITION.md`, `python -m patentpulse.peek` for local SQLite
inspection, and [docs/BUYER_QUICKSTART.md](docs/BUYER_QUICKSTART.md).

## Source and licensing

Patent text and bibliographic records are retrieved from official public USPTO bulk products. The raw source material remains subject to the USPTO's terms and notices. PatentPulse stores source URLs and checksums in `data/manifest.json` to preserve provenance. This repository does not claim ownership of the underlying public records.

The [LICENSE](LICENSE) (source-available proprietary evaluation terms) covers
PatentPulse source code and original documentation only. Commercial use and
acquisition/IP transfer are described in [COMMERCIAL.md](COMMERCIAL.md) and
[docs/acquisition/ASSET_SCHEDULE.md](docs/acquisition/ASSET_SCHEDULE.md).
Publishable data snapshots use Hugging Face's `other` license label, with the
complete reuse notice in [DATA_LICENSE.md](DATA_LICENSE.md). It permits model
training and other reuse only to the extent allowed by applicable law and
underlying rights; it is not a blanket grant for all patent document content
or jurisdictions. USPTO-originated text is not PatentPulse-owned copyright.

For a release checklist, including GitHub tagging and the explicit Hugging Face
upload command, see [docs/RELEASING.md](docs/RELEASING.md).

## Citation

If you use PatentPulse, please cite the USPTO bulk sources and this project. Machine-readable metadata is in [CITATION.cff](CITATION.cff).

```bibtex
@software{patentpulse,
  title  = {PatentPulse: A USPTO full-text patent corpus and ingestion pipeline},
  author = {theworker02},
  year   = {2026},
  url    = {https://github.com/theworker02/patentpulse},
  note   = {Dataset: https://huggingface.co/datasets/theworker02/patentpulse}
}
```

## Related work

PatentPulse follows the dataset-card conventions popularized by large Hugging Face corpora such as [HUPD](https://huggingface.co/datasets/HUPD/hupd), while differing in two important ways:

- it ingests the official weekly source archives directly and retains per-file provenance;
- it includes both published applications and issued grants, with a resumable local backfill rather than a static snapshot.

## License

**Source-available proprietary** — evaluation under [LICENSE](./LICENSE); commercial / production use via [COMMERCIAL.md](./COMMERCIAL.md). See [LICENSE_TRANSITION_NOTICE.md](./LICENSE_TRANSITION_NOTICE.md).
