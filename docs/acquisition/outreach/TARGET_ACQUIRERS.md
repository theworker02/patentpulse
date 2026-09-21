# Target acquirers — PatentPulse

Companies where buying PatentPulse (pipeline + corpus + continuous updater)
can replace or accelerate an internal USPTO full-text data-engineering program.

Priority = strategic fit × likely data appetite × acquisition / partnership
history. Contact status is tracked in this file; pitches live in
[PITCH.md](PITCH.md).

## Tier A — Patent intelligence / IP analytics

| Company | Why PatentPulse fits | Public contact | Outreach status |
| --- | --- | --- | --- |
| **PatSnap** | AI IP/R&D intelligence; large patent graph; continuous US full-text feed reduces ETL cost | `swiley@patsnap.com` (published press contact) | **Sent** 2026-09-21 (`1a0c17a069708d79`) |
| **Questel (Orbit)** | Active IP platform consolidator; Orbit consumers need clean weekly US text | `communication@questel.com` | **Sent** 2026-09-21 (`1a0c17a0dcea7645`) |
| **Clarivate (Derwent / CompuMark IP)** | Incumbent patent data; enrichment overlay on weekly XML is complementary | `newsroom@clarivate.com` | **Sent** 2026-09-21 (`1a0c17a09e02825f`) |
| **IFI CLAIMS / Digital Science** | Patent database + Dimensions; ingest pipeline shortens US refresh cycles | `info@ificlaims.com`, `sales@ificlaims.com`; cc `d.ellis@digital-science.com` | **Sent** 2026-09-21 (`1a0c17a04807398e`) |
| **Ambercite** | Citation/similarity search; needs high-quality full text | `contact@ambercite.com` | **Sent** 2026-09-21 (`1a0c17a046273549`) |
| **IPRally** | Graph/ML prior-art search | Via IFI partner network / website contact | Listed — use website form |
| **Amplified** | AI patent research UX | `info@amplified.ai` | **Sent** 2026-09-21 (`1a0c17a0b0924515`) |
| **PatSeer / Gridlogics** | Analytics + surveillance | Website / sales | Listed |

## Tier B — Legal AI / law-firm tech

| Company | Why PatentPulse fits | Public contact | Outreach status |
| --- | --- | --- | --- |
| **LexisNexis (Lexis+ AI / IP)** | Legal research + patent adjacent products | `ip@lexisnexis.com` | **Sent** 2026-09-21 (`1a0c17a0e0d95680`) |
| **Thomson Reuters (CoCounsel / Westlaw)** | Legal AI stack; patent full text for specialist agents | Corporate BD | Listed |
| **Harvey** | Domain LLM for legal work; patent corpus for specialized tools | Website | Listed |
| **Casetext** (TR) | Legal AI heritage | Via Thomson Reuters | Listed |
| **DeepIP / Solve Intelligence / Specifio** | Patent drafting & prosecution AI — need claims/description corpora | Website contact forms | Listed |
| **Relativity** | Legal data platform; IP practice workflows | Website | Listed |

## Tier C — Prior-art / search vendors

| Company | Why PatentPulse fits | Notes |
| --- | --- | --- |
| **Google Patents / Google** | Already indexes patents; less likely acquirer, possible data partnership | Low probability buy |
| **IP.com** | Innovation / prior-art search | Channel partner programs |
| **Minesoft / XLPAT** | Patent search platforms | Sales-led |
| **GreyB** | Search + invalidity services | Services + tools hybrid |
| **PatentCloud (Wisdomain)** | Asia-focused patent platforms expanding US text | Sales |

## Tier D — Scientific information & AI-data companies

| Company | Why PatentPulse fits | Public contact | Outreach status |
| --- | --- | --- | --- |
| **Digital Science (Dimensions)** | Science + patents graph; IFI sibling | `d.ellis@digital-science.com` | Combined with IFI outreach |
| **Elsevier (Scopus / ScienceDirect)** | Scientific corpus + patent adjacency | Corporate BD | Listed |
| **Springer Nature** | Research content platforms | Corporate BD | Listed |
| **Semantic Scholar / Ai2** | Research AI; patent text as scientific prior art | Via allenai.org contact | Listed |
| **Hugging Face** | Already hosts the snapshot; possible dataset partnership / spotlight | Dataset discussion channels | Listed |
| **Scale AI / Surge / other data vendors** | Sell licensed training corpora to model labs | BD emails via websites | Listed |
| **OpenAI / Anthropic / Google DeepMind / Meta AI (data partnerships)** | Training / tooling data — partnership more likely than acquisition | Research/data partnership forms | Listed as partnership track |

## Messaging angle by category

1. **Patent intelligence:** “Drop-in US weekly full-text ETL with provenance and a 5.93M Parquet snapshot — months of data engineering already done.”
2. **Legal AI:** “Claims + description ready for drafting, search, and RAG without standing up USPTO XML ops.”
3. **Prior-art vendors:** “Higher recall text layer with temporal splits for eval; continuous sync keeps indexes fresh.”
4. **Scientific / AI-data:** “Provenance-preserving technical corpus adjacent to papers; Hub-ready shards for training pipelines.”

## Diligence assets to attach

- GitHub: https://github.com/theworker02/patentpulse
- Hub: https://huggingface.co/datasets/theworker02/patentpulse
- Data room: `docs/acquisition/` in-repo
- Metrics JSON: `docs/acquisition/metrics/acquisition_metrics.json`
