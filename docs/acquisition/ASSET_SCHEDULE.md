# Asset schedule — PatentPulse Acquisition Release 1.0

This schedule states what transfers in an acquisition or IP-transfer discussion, and what does **not**. The distinction between PatentPulse-owned software, USPTO-originated material, and third-party/open-source dependencies is material to diligence.

It is a diligence aid, not a signed purchase agreement. Final schedules of assets, exclusions, and reps/warranties are negotiated in definitive documents.

## A. Transferable PatentPulse assets (seller-owned / controllable)

Subject to negotiation, exclusivity, and customary closing conditions, the following are intended to transfer:

| Asset | Description |
| --- | --- |
| **Source code & copyright** | PatentPulse Python package (`patentpulse/`), scripts, tests, examples, and original documentation authored for this project, under copyright held by theworker02 / Matthew Looney, on the terms of the proprietary source-available LICENSE (or successor commercial assignment). |
| **Brand** | “PatentPulse” name as used in this repository, logo (`assets/patentpulse-logo.svg`), and associated badges/wording in project docs. |
| **Documentation** | README, dataset card, releasing docs, acquisition data room, buyer demo runbook, corpus-finish procedure, commercial/licensing notices authored for PatentPulse. |
| **Schemas** | Normalized record schema, SQLite DDL usage, Arrow/Parquet field contract, HUPD-compatible aliases. |
| **Ingestion / normalization logic** | ODP/BDSS fetch, constant-memory XML stream parse, extract/clean, identity keys, resumable manifest, sync loop. |
| **Tests** | `tests/` suite and fixtures (synthetic XML; not USPTO dumps). |
| **Manifests / provenance system** | `IngestManifest` design, release_manifest generation, digest computation, metrics CLI. |
| **Release tooling** | `patentpulse.hf_release` exporter/validator, Hub card generation, acquisition metrics packet. |
| **Acquisition materials** | Teaser, asset schedule, outreach templates, target-acquirer lists, measured JSON under `docs/acquisition/`. |
| **Domain / accounts (where transferable)** | GitHub repository transfer; Hugging Face dataset repo transfer or dual-control handoff; related project emails/usernames **only if** the seller can assign them under platform terms. USPTO API keys are personal/operator credentials and are **re-issued**, not sold as a secret. |
| **Unpublished / private material** | Operator `data/manifest.json`, local JSONL/SQLite working copies, private notes, and any non-public evaluation package shared under NDA — transferred or destroyed per agreement. |
| **Transition period** | Agreed handoff window (typical discussion: 30–90 days) for environment walkthrough, one re-export assist, and Q&A. Ongoing employment/consulting is optional and separately scoped. |

## B. USPTO-originated material (does **not** transfer as owned IP)

| Item | Treatment |
| --- | --- |
| Weekly grant/application full-text XML and ZIP dumps | Obtained from USPTO Open Data Portal / Bulk Data; reuse governed by [USPTO Terms of Use](https://www.uspto.gov/terms-use-uspto-websites) and [DATA_LICENSE.md](../../DATA_LICENSE.md). |
| Patent document text (title, abstract, claims, description, CPC as published, etc.) | Government-produced / applicant-authored content; PatentPulse does not claim copyright ownership of USPTO document text. |
| Published Hub snapshot rows | A **normalized representation** of USPTO material with PatentPulse tooling provenance. Buyer receives the files and the right to continue operating the pipeline; buyer does **not** receive a proprietary copyright grant covering third-party or USPTO text beyond what law and USPTO terms already allow. |
| USPTO trademarks, seals, logos | Not transferred; do not imply endorsement. |

## C. Third-party / open-source dependencies (not PatentPulse-owned)

Runtime and tooling dependencies retain their own licenses. At Acquisition Release 1.0 the declared direct Python dependencies are:

| Package | Role | License (as typically published upstream) |
| --- | --- | --- |
| `lxml` | XML parse | BSD-3-Clause (and libxml2/libxslt LGPL where applicable) |
| `pyarrow` | Parquet/Arrow I/O | Apache-2.0 |
| `pytest` (dev) | Tests | MIT |
| `huggingface_hub` / `datasets` (optional Path A) | Hub load/metrics | Apache-2.0 |

Buyers must comply with those licenses independently. Historical git revisions of PatentPulse that were published under MIT remain under those historical terms for copies obtained while MIT applied; the current tree is proprietary ([LICENSE_TRANSITION_NOTICE.md](../../LICENSE_TRANSITION_NOTICE.md)).

Related research corpora (e.g. HUPD) are **not** included assets; PatentPulse only provides field-name compatibility aliases.

## D. Explicitly excluded unless separately agreed

- Hosted subscription SaaS, multi-tenant search UI, or customer contracts (none are part of this freeze as a product line).
- Non-USPTO jurisdictions (EPO, WIPO, CN, JP, …).
- Drawings, sequence listings as structured biological data, PAIR prosecution histories.
- Any asking price, earn-out, or exclusivity term (negotiated after buyer qualification).

## E. Suggested transfer package language (for counsel)

> Seller assigns all right, title, and interest in the PatentPulse software, documentation, brand, schemas, tests, provenance/release tooling, and acquisition materials listed in Schedule A, together with an agreed transition-assistance period. USPTO-originated patent text and third-party open-source components are identified in Schedules B and C and are not represented as Seller-owned copyright beyond Seller’s original expression and compilation/tooling.

## F. Buyer qualification before price

Outreach and teasers use: **seeking acquisition or IP transfer discussions** — no public asking price. Price, exclusivity, transition scope, and post-close involvement are negotiated only after a buyer confirms roadmap relevance and reviews diligence materials.
