# Dataset Card: PatentPulse

## Dataset summary

PatentPulse is a local, provenance-preserving corpus assembled from official USPTO weekly XML releases:

- `PTGRXML`: issued patent grants, full text, no images
- `APPXML`: published patent applications, full text, no images

The corpus is intentionally incremental. `data/manifest.json` is the authority for which weekly source archives have been processed, their source URLs, checksums, and extraction counts.

The project is inspired by the field structure and data-card conventions of [The Harvard USPTO Patent Dataset (HUPD)](https://huggingface.co/datasets/HUPD/hupd), but it is not a copy of HUPD and does not include HUPD-only prosecution or decision labels.

## Hugging Face distribution

The local append-only JSONL is an ingestion artifact, not a distributable Hub
format: older rows can have a smaller field set and local provenance paths. Use
`python -m patentpulse.hf_release export` to create an immutable Parquet
release. The exporter normalizes every row to one Arrow schema, derives the
documented aliases, creates temporal splits, strips local directories from
`source_file`, writes a release manifest, and generates an HF `README.md` with
YAML metadata. It refuses to run while the ingestion manifest is incomplete or
when free disk space is insufficient.

## Supported use cases

- Technical semantic search and retrieval-augmented generation
- CPC-conditioned classification
- Patent language modeling
- Claims-to-abstract summarization research
- Prior-art discovery experiments
- Temporal studies of patent terminology

## Out-of-scope use cases

- Legal validity, infringement, novelty, freedom-to-operate, or patentability determinations
- Automated decisions materially affecting people or organizations
- Interpreting an absent field as evidence that it does not exist in the original filing
- Treating patent publication data as evidence of technical correctness, commercial value, or enforceability

## Data instances

Each row represents one USPTO grant or published application document.

### Canonical fields

| Field | Type | Description |
| --- | --- | --- |
| `patent_grant_id` | string/null | USPTO publication/grant identifier without country prefix |
| `application_number` | string/null | USPTO application number |
| `publication_date` | ISO date/null | Publication or grant issue date |
| `invention_title` | string/null | Normalized invention title |
| `abstract_text` | string/null | Normalized abstract |
| `claims_text` | string/null | Flattened legal claims |
| `description_text` | string/null | Cleaned full description |
| `primary_cpc_codes` | list[string] | Main CPC label(s) reported by the source |
| `further_cpc_codes` | list[string] | Additional CPC labels where available |
| `ipc_codes` | list[string] | IPC labels where available |
| `document_type` | `grant` / `application` | Source family |
| `filing_date` | ISO date/null | Application filing date, when present |
| `kind_code` | string/null | Publication/grant kind code |
| `source_file` | string/null | Local source archive path |
| `cited_patent_ids` | list[string] | Patent citations from the weekly XML (`patcit`) |
| `npl_citations` | list[string] | Non-patent literature citations, truncated |
| `related_application_numbers` | list[string] | Related/parent application numbers when present |

### HUPD-compatible aliases

The JSONL output also emits aliases to simplify downstream adapters:

| PatentPulse | Alias |
| --- | --- |
| `patent_grant_id` | `patent_number`, `publication_number` |
| `invention_title` | `title` |
| `abstract_text` | `abstract` |
| `claims_text` | `claims` |
| `description_text` | `full_description` |
| `publication_date` | `date_published` |
| `primary_cpc_codes[0]` | `main_cpc_label` |
| combined CPC labels | `cpc_labels` |

PatentPulse does **not** currently provide HUPD fields that require prosecution data or non-XML sources, including decision, abandon date, small-entity indicator, examiner ID, and foreign-filing indicator.

## Collection process

1. Query the USPTO Open Data Portal for the official weekly catalog.
2. Download an archive.
3. Stream it: weekly XML payloads concatenate thousands of separate XML documents.
4. Parse each document with `lxml`.
5. Normalize text without removing technical notation.
6. Save record-level content to SQLite and JSONL.
7. Record the archive's source URI, SHA-256, status, and counts in the manifest.

Sequence-listing and other non-patent companion XML documents are skipped. Parse failure counts are recorded per weekly file; a completed manifest entry does not imply every XML block was a patent record.

## Preprocessing

- Unicode NFKC normalization
- XML/HTML entity decoding
- Whitespace normalization
- Structural XML flattening
- Removal of repeated legal front matter, including cross-reference and government-interest blocks
- Preservation of claims numbering, symbols, units, variable names, and headings where possible

Descriptions are cleaned for ML and retrieval use. They are not a legally authoritative rendering of the original XML.

## Splits and evaluation

Use temporal splits rather than random splits for most predictive tasks. A recommended pattern:

```text
train: publication dates before 2025-01-01
validation: 2025 calendar year
test: 2026 calendar year
```

For claims-to-abstract summarization, use `claims_text` as input and `abstract_text` as target, while filtering out empty or very short values. For CPC classification, predict `main_cpc_label` from title, abstract, claims, or description.

## Known limitations

- The dataset is a backfill in progress; coverage is incomplete until all manifest entries are complete.
- XML schemas and field availability vary over time, especially in historic data.
- Design and plant patents commonly have sparse abstracts, claims, or CPC data.
- CPC labels can be incomplete or absent in a particular weekly record.
- Text extraction does not preserve tables, equations, images, drawings, chemical structures, or sequence files as structured modalities.
- Grant and application documents can refer to related inventions; they are not deduplicated into patent families.
- Reissues and corrected releases can appear as separate official weekly files.

## Bias, privacy, and sensitive content

Patent documents are public technical and legal filings. They may contain inventor names, locations, organizations, and terminology that is outdated, biased, or offensive. They also reflect unequal access to the patent system and differences in national, industrial, and institutional participation. Models trained on this corpus can reproduce these patterns.

## Provenance and reproducibility

For every successfully ingested weekly archive, `data/manifest.json` stores:

- the exact official source URL
- source filename
- SHA-256 digest
- extracted record and parse-failure counts
- ingestion timestamp

Do not delete the manifest when regenerating local outputs.

## Licensing and attribution

Raw records originate from USPTO public bulk products. The PatentPulse code and
original documentation are MIT-licensed; a published data snapshot is labeled
`other` on Hugging Face because the project cannot issue a blanket license for
every underlying patent document worldwide. See [DATA_LICENSE.md](DATA_LICENSE.md)
for the complete reuse notice.

PatentPulse imposes no additional restriction against machine-learning training
or research use, but users must review the [USPTO Terms of
Use](https://www.uspto.gov/terms-use-uspto-websites), respect third-party
rights, assess their jurisdiction, and retain the requested source
acknowledgement. Do not imply USPTO endorsement or use USPTO marks.

## Citation

If using the dataset design or writing about the format, cite the official USPTO bulk products and consider citing HUPD for the structured patent-dataset approach:

```bibtex
@inproceedings{suzgun2023the,
  title={The Harvard USPTO Patent Dataset: A Large-Scale, Well-Structured, and Multi-Purpose Corpus of Patent Applications},
  author={Suzgun, Mirac and Melas-Kyriazi, Luke and Sarkar, Suproteem K. and Kominers, Scott and Shieber, Stuart},
  booktitle={NeurIPS Datasets and Benchmarks},
  year={2023}
}
```
