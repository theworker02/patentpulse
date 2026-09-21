# Quality metrics

Hard quality measurements for the published Hugging Face snapshot
`theworker02/patentpulse` (release `2026-08-28`, canonical digest
`42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944`).

Reproduce:

```bash
python scripts/compute_acquisition_metrics.py \
  --output docs/acquisition/metrics/acquisition_metrics.json
```

## Split integrity

| Split | Records | Parquet shards |
| --- | --- | --- |
| train | 4,676,062 | 34 |
| validation | 772,091 | 6 |
| test | 481,311 | 4 |
| **Total unique** | **5,929,464** | **44** |

Temporal policy (documented in the dataset card): train before 2025-01-01;
validation = 2025; test = 2026.

## Field fill rates (sampled)

Sample: **18,168 rows** across row groups from `train/part-00000` and
`validation/part-00000` (not a full census). Document-type mix in sample:
12,003 grants · 6,165 applications.

| Field | Nonempty |
| --- | --- |
| `patent_grant_id` | 100% |
| `application_number` | 100% |
| `publication_date` | 100% |
| `document_type` | 100% |
| `source_file` | 100% |
| `claims_text` | **100%** |
| `invention_title` | **99.82%** |
| `description_text` | **99.28%** |
| `abstract_text` | **90.94%** |
| `main_cpc_label` / `primary_cpc_codes` / `cpc_labels` | **90.84%** |
| `kind_code` | 0% in published sample |
| `filing_date` | 0% in published sample |
| `further_cpc_codes`, `ipc_codes` | 0% in published sample |
| `assignee_names`, `inventor_list` | 0% in published sample |
| `cited_patent_ids`, `npl_citations` | 0% in published sample |

### Interpretation

- Core ML text fields (title, abstract, claims, description) and primary CPC
  are strong in the published snapshot.
- Abstract/CPC gaps are expected for some design/plant and sparse weekly rows.
- **Bibliographic enrichment fields are empty in the v1 Hub snapshot** despite
  being implemented in the current pipeline (`tests/test_pipeline.py` asserts
  inventors, assignees, citations, filing date, kind code on the fixture).
  Diligence conclusion: treat v1 as a **full-text + primary CPC** corpus;
  plan a **re-ingest/re-export** for inventor/assignee/citation completeness.

## Text length distributions (sampled nonempty values)

| Field | Mean chars | p50 | p90 | p99 | Max |
| --- | --- | --- | --- | --- | --- |
| `invention_title` | 55 | 52 | 97 | 154 | 336 |
| `abstract_text` | 714 | 743 | 962 | 1,260 | 3,763 |
| `claims_text` | 6,382 | 5,872 | 11,207 | 20,533 | 140,619 |
| `description_text` | 63,286 | 47,320 | 125,872 | 326,065 | 1,969,457 |

## Pipeline contract tests

```bash
python -m pytest tests -q
```

As of this data-room build: **11 passed**. Tests cover concatenated XML
splitting, cleaning, bibliographic/CPC extraction, SQLite/JSONL writers, and
HF release validation helpers.

## Recommended buyer acceptance checks

1. Confirm `release_manifest.json` digest matches
   `42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944`.
2. Spot-check ≥1,000 streamed rows for nonempty claims + description.
3. After any fresh ingest, assert inventor/assignee/citation fill rates on a
   recent grant week before cutting a v2 release.
