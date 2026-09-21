# Build versus buy

Acquiring PatentPulse is a data-engineering substitution, not a search-product substitution. The table is what an internal team still has to invent if they start from USPTO weekly XML.

| Workstream | Without PatentPulse | With PatentPulse |
| --- | --- | --- |
| Discover official weekly grant and application dumps | ODP catalog + BDSS fallback, product IDs, filename conventions | `patentpulse.ingest fetch` / `sync` |
| Stream concatenated XML (not one tree per file) | Custom splitter, max-document caps, ZIP/TAR/GZ readers | `patentpulse.stream` |
| Constant-memory parse | `iterparse`, DTD variety, sequence-listing skip | `patentpulse.extract` + `parse` |
| Text cleaning | Entity decode, PI artifacts, boilerplate vs headings | `patentpulse.clean` |
| Identity and crash safety | Unique keys, WAL, replay, locks, atomic manifests | `schema` + `manifest` + ingest lock |
| Dedup across retries | Global key set on 6.5M JSONL rows | 570,714 duplicates already removed in the public snapshot |
| Schema stability | One Arrow schema, aliases, no local paths | `hf_release` exporter |
| Temporal splits | Leakage-safe train/val/test by publication year | Already applied |
| Rights posture | MIT-vs-USPTO confusion | Explicit `other` label + [DATA_LICENSE.md](../../DATA_LICENSE.md) |
| Provenance | Per-week URL, SHA-256, counts | Manifest contract (local pipeline) |
| Quality evidence | Someone has to measure fill rates on 5.93M rows | This data room |

## Calendar reality (not a quote)

A competent data team can prototype a parser in a sprint. Productionizing weekly USPTO full text through schema drift, torn JSONL, disk guards, and a 200 GB Parquet release is the long pole. PatentPulse's published snapshot is already past that pole: 5.93 million unique rows, 8.78% duplicate mass removed, 186 malformed lines quarantined, 44 shards with footer-verified fill rates.

What the buyer still builds: retrieval, embeddings, family grouping, non-US collections, drawings, prosecution data, and the product UI. Those are product months. They should not be spent re-deriving `us-patent-grant` concatenated XML.

## Cost shape

- **No GPU** for ingest or snapshot production.
- **~212 GB** to hold the published Parquet.
- **~0.9 TB** if the buyer keeps the JSONL artifact.
- **Transient ZIP space** during backfill (archives deleted by default).
- One USPTO ODP API key for Path B.

Raw USPTO text is public. The expensive part is a trustworthy, replayable, rights-labeled corpus. That is what is for sale.
