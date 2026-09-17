# PatentPulse

PatentPulse is a locally owned, continuously growing corpus of USPTO patent grants and published applications. It downloads official weekly XML dumps, stream-parses them without loading an archive into memory, and writes normalized SQLite and JSON Lines outputs for search, tokenization, embeddings, and model training.

It is a local data project, not a Python package intended for publication.

## Dataset at a glance

| Property | Value |
| --- | --- |
| Sources | USPTO Patent Grant Full-Text XML (`PTGRXML`) and Patent Application Full-Text XML (`APPXML`) |
| Cadence | Weekly — grants on Tuesday; applications on Thursday |
| Storage | SQLite + UTF-8 JSON Lines |
| Primary text | Title, abstract, claims, cleaned description |
| Core labels | Document type, publication date, CPC |
| Backfill coverage | Tracked in `data/manifest.json` |

Run the current inventory:

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

# Parse a downloaded XML or ZIP into SQLite
python -m patentpulse.parse `
  --input data/raw/grants/ipgYYMMDD.zip `
  --output data/processed/patents.db `
  --format sqlite
```

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
├── manifest.json              # Per-week source inventory and ingestion status
├── raw/                       # Temporary / manually supplied USPTO archives
└── processed/
    ├── patents.db             # Normalized SQLite corpus
    └── patents.jsonl          # One dataset record per line
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
        │
        ▼
stream.py     splits concatenated XML documents
        │
        ▼
extract.py    normalizes bibliographic and full-text fields
        │
        ▼
clean.py      removes XML artifacts and repetitive front matter
        │
        ▼
schema.py     batches SQLite and JSONL writes
        │
        ▼
manifest.py   makes backfill resumable and auditable
```

## Quality and validation

```powershell
python -m pytest tests -q
```

The test suite verifies concatenated-document splitting, text cleaning, bibliographic/CPC extraction, and SQLite/JSONL output.

## Source and licensing

Patent text and bibliographic records are retrieved from official public USPTO bulk products. The raw source material remains subject to the USPTO's terms and notices. PatentPulse stores source URLs and checksums in `data/manifest.json` to preserve provenance. This repository does not claim ownership of the underlying public records.

The [MIT License](LICENSE) covers PatentPulse source code and original
documentation only. Publishable data snapshots use Hugging Face's `other`
license label, with the complete reuse notice in [DATA_LICENSE.md](DATA_LICENSE.md).
It permits model training and other reuse only to the extent allowed by
applicable law and underlying rights; it is not a blanket grant for all patent
document content or jurisdictions.

For a release checklist, including GitHub tagging and the explicit Hugging Face
upload command, see [docs/RELEASING.md](docs/RELEASING.md).

## Related work

PatentPulse follows the dataset-card conventions popularized by large Hugging Face corpora such as [HUPD](https://huggingface.co/datasets/HUPD/hupd), while differing in two important ways:

- it ingests the official weekly source archives directly and retains per-file provenance;
- it includes both published applications and issued grants, with a resumable local backfill rather than a static snapshot.
