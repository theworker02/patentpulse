# PatentPulse acquisition / partnership pitch

Use this copy for email, decks, and BD calls. Keep claims tied to measured
metrics in `docs/acquisition/metrics/`.

## One-sentence pitch

PatentPulse is a production USPTO weekly full-text ingestion pipeline plus a
5.93-million-record Parquet corpus — so your team can ship patent search, RAG,
and training features without spending the next few quarters rebuilding USPTO
XML ETL.

## Email subject lines (pick one)

1. PatentPulse: 5.93M USPTO full-text records + resumable weekly ingest
2. Acquire months of USPTO data engineering in one transfer
3. Provenance-preserving US patent corpus (Parquet) for your AI/IP stack

## Short email body (≈180 words)

Hi {Name},

I’m reaching out about **PatentPulse**, an open pipeline and published dataset
that turns official USPTO weekly grant and application XML into normalized
full text (title, abstract, claims, description, CPC) with per-archive
provenance.

**What you’d get**
- 5,929,464 unique records (2018–2026 window) as Zstd Parquet on Hugging Face
- ~211 GB compressed / ~874 GB source JSONL / ~967 GB estimated uncompressed Parquet
- Resumable ODP sync, stream parsing, SQLite+JSONL writers, guarded release exporter
- Measured release hygiene: 8.78% dedup of retry rows removed; 0.0029% malformed JSON skipped
- Reproducible buyer deploy runbook and quality metrics in our acquisition data room

For patent-intelligence, legal-AI, prior-art, or scientific-data products, this
typically replaces a multi-quarter internal data-engineering effort with a
days-to-wire integration.

Repo: https://github.com/theworker02/patentpulse  
Dataset: https://huggingface.co/datasets/theworker02/patentpulse  

Happy to share the data room and walk through diligence on a 30-minute call.

Best,  
{Sender}  
{Email}  
{GitHub: theworker02}

## Longer pitch bullets (call / deck)

**Problem.** USPTO delivers patents as weekly concatenated XML dumps. Building
reliable, resumable, provenance-preserving full-text ETL is slow, easy to get
wrong, and orthogonal to product differentiation.

**Solution.** PatentPulse already:
1. Catalogs and downloads ODP weekly products with checksums
2. Stream-parses multi-document archives in constant memory
3. Cleans text without destroying technical notation
4. Writes queryable SQLite and ML-friendly JSONL
5. Exports immutable temporal-split Parquet with a content digest

**Evidence.**
- 5.93M unique Hub records; digest `42d3a4ae…4944`
- Claims 100% / description 99.3% / abstract 90.9% nonempty in quality sample
- ~1.5k docs/s fixture-scale e2e parse on Linux x86_64 (reproducible script)
- MIT code; transparent data-rights notice for USPTO-sourced text

**Deal shapes.** Asset purchase of repo + dataset; exclusive commercial license;
OEM data feed; or acqui-hire / advisory for continuous backfill ops.

**Ask.** Technical diligence call; NDA if needed for private mirror sizing and
roadmap (family keys, richer bibliographic backfill, non-US offices).

## Objection handling

| Objection | Response |
| --- | --- |
| “We already license Derwent/IFI.” | PatentPulse is complementary raw full-text + owned ETL — useful for AI features, eval sets, and reducing dependency on a single feed. |
| “We’ll just scrape Google Patents.” | Weekly official XML + checksums + manifest beats brittle HTML; legal/ops risk differs. |
| “Bibliographic fields look sparse on Hub.” | Disclosed: v1 snapshot is full-text heavy; current extractor fills inventors/assignees/citations — re-ingest/re-export is the fix, documented in the data room. |
| “Is the data MIT-licensed?” | Code is MIT; data is labeled `other` with USPTO attribution — see DATA_LICENSE.md. |

## Call-to-action links

- Data room index: `docs/acquisition/README.md`
- Executive summary: `docs/acquisition/EXECUTIVE_SUMMARY.md`
- Buyer deploy: `docs/acquisition/BUYER_DEPLOYMENT.md`
