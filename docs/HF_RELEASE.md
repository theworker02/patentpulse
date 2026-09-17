# Hugging Face release workflow

PatentPulse releases are immutable, normalized Parquet snapshots. The local
SQLite and append-only JSONL files are ingestion artifacts and are not uploaded
to Hugging Face.

## Preconditions

1. Finish the ingestion manifest. The release command intentionally stops when
   any source is `pending`, `running`, or `failed`.
2. Use a separate volume with enough free space for the compressed release. The
   command estimates the projected output from the input size, adds 20% working
   headroom, enforces a 2 GB minimum, and refuses an unsafe full conversion.
3. Confirm the distribution terms for the intended jurisdiction. The generated
   card uses the Hugging Face `other` license value because USPTO records can
   include third-party material and the USPTO reserves international rights.
   Read [DATA_LICENSE.md](../DATA_LICENSE.md) before publishing; it explains
   why the MIT code license is not a blanket data license.

## Build and validate

Run a small, non-publishable smoke export first:

```powershell
python -m patentpulse.hf_release export `
  --input data/processed/patents.jsonl `
  --output C:\releases\patentpulse-smoke `
  --max-records 10000
```

Build the immutable full release on a volume with adequate capacity:

```powershell
python -m patentpulse.hf_release export `
  --input data/processed/patents.jsonl `
  --output E:\releases\patentpulse-v1
```

Validate it again before upload:

```powershell
python -m patentpulse.hf_release validate --release E:\releases\patentpulse-v1
```

The export writes only these publishable files:

```text
README.md                 # Hugging Face dataset card and YAML metadata
DATA_LICENSE.md           # dataset-rights and training-use notice
release_manifest.json     # immutable release counts and digest
data/
  train/*.parquet
  validation/*.parquet
  test/*.parquet
  unspecified/*.parquet
```

Each Parquet shard has one explicit schema, uses Zstandard compression, targets
5 GB, and uses 64 MB row groups. A completed shard can exceed its target by at
most one row group because Parquet row groups are atomic. Source paths are reduced to archive
filenames so local usernames and workstation directories are not published. The
export also deduplicates append-only retry rows globally by document type,
publication identifier, application number, and publication date.

## Upload

Creating a Hugging Face repository and uploading data are intentionally
separate, explicit actions. After validation and repository creation, upload
the release contents with:

```powershell
hf upload <namespace>/patentpulse E:\releases\patentpulse-v1 --type dataset
```

Do not upload `data/processed/patents.jsonl`, `patents.db`, WAL files, raw
archives, or the local ingestion manifest.
