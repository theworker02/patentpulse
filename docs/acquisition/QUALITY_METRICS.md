# Quality metrics

All published-snapshot fill rates below come from Parquet footer statistics on **every** shard (`44/44` succeeded, `0` footer errors, `5,929,464` rows). No row-group payloads were downloaded. Recompute with `python -m patentpulse.metrics`.

Local extraction quality was measured on 400 unique records expanded from `tests/fixtures/sample_bulk.xml`.

## Published snapshot fill rates

| Field | Fill rate | Nulls / 5,929,464 |
| --- | ---: | ---: |
| `patent_grant_id` | 100.000% | 0 |
| `application_number` | 100.000% | 0 |
| `publication_date` | 100.000% | 0 |
| `claims_text` | 100.000% | 0 |
| `document_type` | 100.000% | 0 |
| `source_file` | 100.000% | 0 |
| `invention_title` / `title` | 99.890% | 6,529 |
| `description_text` / `full_description` | 99.111% | 52,695 |
| `abstract_text` / `abstract` | 94.669% | 316,097 |
| `main_cpc_label` / `primary_cpc_codes` | 94.612% | 319,480 |
| `kind_code`, `country`, `language`, `filing_date`, `date_produced`, `application_type`, `claim_count` | 60.290% | 2,354,592 |
| `inventor_list.inventor_name_last` | 60.290% | 2,354,592 |
| `ipc_codes` | 57.555% | 2,516,747 |
| `further_cpc_codes` | 55.073% | 2,663,956 |
| `background` | 53.808% | 2,738,926 |
| `patent_issue_date` | 49.844% | 2,973,964 |
| `summary` | 42.882% | 3,386,764 |
| `assignee_names` | 37.672% | 3,695,708 |
| `examiner_name_last` | 29.860% | 4,158,940 |
| `cited_patent_ids` | 29.693% | 4,168,852 |

`patent_issue_date` is defined only for grants, so a ~50% fill rate is consistent with a mixed grant/application corpus, not with a broken column.

The 60.29% cluster (`kind_code`, `filing_date`, inventor names, `claim_count`, and several bibliographic extras) is a **schema-evolution gap**, not random missingness: those columns were added after part of the append-only JSONL had already been written. A buyer who re-extracts from weekly XML with the current parser fills them on new ingests. Rebuilding historical weeks is optional.

Empty-list nested columns (`further_cpc_codes`, citations) use Parquet null counts on list elements. Treat those as "no values stored," not as XML proof that the USPTO omitted the field.

## Alias and cleaning contract (fixture sample, n=400)

| Check | Rate |
| --- | ---: |
| HUPD aliases match canonical text fields | 100% |
| Publication dates are ISO `YYYY-MM-DD` | 100% |
| Title, abstract, and claims present | 100% |
| `CROSS-REFERENCE` boilerplate leaked into description | 0% |
| Duplicate record keys | 0 |

Current-parser records also populate `kind_code`, `filing_date`, inventors, assignees, examiner names, and citations when the XML contains them. That is why the fixture sample is 100% on core bibliographic extras while the published snapshot is not.

## Column storage concentration

Decoded Parquet pages (uncompressed) are dominated by description text. Aliases duplicate the same bytes:

| Column | Uncompressed pages | Compressed pages |
| --- | ---: | ---: |
| `description_text` | 402.79 GB | 89.20 GB |
| `full_description` (alias) | 402.79 GB | 89.20 GB |
| `summary` | 51.24 GB | 10.37 GB |
| `claims_text` / `claims` | 39.51 GB each | 6.22 GB each |
| `background` | 19.69 GB | 5.12 GB |
| `abstract_text` / `abstract` | 3.99 GB each | 1.17 GB each |

A buyer that drops alias columns at ingest saves roughly half of description and claims storage without losing information.

## Known quality issues to budget for

1. **Hub viewer** cannot infer a shared format because the published card still lists an empty `unspecified` split. Fixed in this pipeline; the live Hub card still needs the patch in [HUB_VIEWER_FIX.md](HUB_VIEWER_FIX.md).
2. **Historical JSONL** lacked later bibliographic columns. Re-extract those weeks if examiner, inventor, or filing-date coverage is a product requirement.
3. **Design and plant patents** are expected to have sparse abstracts, claims, or CPC labels. The 5.3% abstract-null and 5.4% CPC-null rates are not all parser failures.
4. **No patent-family collapse.** Grants and applications that refer to the same invention remain separate rows, by design.

Raw JSON: [metrics/quality_report.json](metrics/quality_report.json), [metrics/parquet_inventory.json](metrics/parquet_inventory.json).
