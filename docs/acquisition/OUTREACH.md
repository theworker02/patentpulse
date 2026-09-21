# Outreach

## Pitch (plain text)

Subject: PatentPulse — 5.93M USPTO full-text records, pipeline included

PatentPulse is a locally owned USPTO grants-and-applications corpus plus the weekly ingest pipeline that produced it. I am opening an acquisition conversation because buying it is cheaper than standing up an internal USPTO XML team.

Measured snapshot (Hugging Face `theworker02/patentpulse`, 2026-08-28):

- 5,929,464 unique full-text records (train/val/test by publication year)
- 6,500,178 valid JSONL rows in; 570,714 duplicates removed (8.78%); 186 malformed lines quarantined (0.00286%)
- 873.81 GB uncompressed JSONL → 211.41 GB Zstd Parquet (44 shards)
- 100% fill on grant id, application number, publication date, claims, document type
- 99.89% titles, 99.11% descriptions, 94.67% abstracts, 94.61% primary CPC
- Canonical digest 42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944

The code stream-parses official weekly XML in constant memory, writes SQLite and JSONL, and exports a single Arrow schema with HUPD-compatible aliases. A 4-vCPU box parses 1,465 fixture docs/s and skips 100% of rows on replay into the same SQLite file.

This is the work your data engineers would otherwise spend the next several months on: concatenated Red Book dumps, DTD drift, identity keys, torn-write JSONL, disk guards, and a rights notice that does not pretend MIT covers every patent document.

I am not asking you to license a search UI. I am asking whether your corp-dev or data platform team wants the corpus and the plant.

Links:

- Pipeline: https://github.com/theworker02/patentpulse
- Snapshot: https://huggingface.co/datasets/theworker02/patentpulse
- Data room: https://github.com/theworker02/atlas-of-knowledge/blob/cursor/patentpulse-acquisition-data-room-e1fd/docs/patentpulse-acquisition/README.md
- Packet PR: https://github.com/theworker02/atlas-of-knowledge/pull/1

Matthew Looney
matthewlooney5@gmail.com
https://github.com/theworker02

## Contact log

Emails are sent only to addresses published on the company's own site or company page, as general sales/partnerships inboxes, not personal employee inboxes.

| Date (UTC) | Company | Category | Address | Status |
| --- | --- | --- | --- | --- |
| 2026-09-21 | IPRally | Prior-art / search | sales@iprally.com | sent (`1a0c1891c27353a6`) |
| 2026-09-21 | PatSnap | Patent intelligence | demo-inquiry@patsnap.com | sent (`1a0c1891f6d982dd`) |
| 2026-09-21 | Amplified | Prior-art / search | info@amplified.ai | sent (`1a0c18920f554281`) |
| 2026-09-21 | Minesoft | Patent intelligence | info@minesoft.com | sent (`1a0c1897fbb82888`) |
| 2026-09-21 | Questel | Patent intelligence | communication@questel.com | sent (`1a0c18980e3f3173`) |
| 2026-09-21 | Luminance | Legal-AI | info@luminance.com | sent (`1a0c189827bd6137`) |
| 2026-09-21 | Digital Science | Scientific information | info@digital-science.com | sent (`1a0c189dc3733207`) |
| 2026-09-21 | Snorkel AI | AI-data | info@snorkel.ai | sent (`1a0c189dff12afd7`) |
| 2026-09-21 | Hugging Face | AI-data | website@huggingface.co | sent (`1a0c189e00ae1d67`) |

Companies with partnership **forms only** (Clarivate IP, Harvey, Cohere, Together AI, Thomson Reuters, LexisNexis IP, CAS, Allen AI) are listed in [TARGET_ACQUIRERS.md](TARGET_ACQUIRERS.md) and were not cold-emailed to privacy or recruiting inboxes.
