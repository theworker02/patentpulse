# Target acquirers

PatentPulse is useful to a buyer that already sells search, analytics, or models on technical documents and currently spends internal engineering on USPTO XML. It is a poor fit for a firm that only wants a hosted docketing UI with no data team.

Each row is a company where owning this corpus and pipeline can replace an internal USPTO full-text ingest program.

## Patent intelligence

| Company | Why an acquisition lands | Public entry |
| --- | --- | --- |
| Clarivate (Derwent, Cortellis, IP Group) | Derwent already commercializes value-added patent content. A local, provenance-preserving USPTO full-text layer plus weekly sync is months of DE they should not redo for every new AI surface. | [IP contact](https://clarivate.com/intellectual-property/contact-us/) |
| Questel | Orbit/FAMPAT buyers expect complete full text. Questel already partners for data adjacency; a ready USPTO XML→Parquet plant is a cheaper alternative to another internal parser. | communication@questel.com |
| PatSnap | AI-native patent analytics needs clean title/abstract/claims/description at 5.93M scale with CPC labels. | demo-inquiry@patsnap.com, hello@patsnap.com |
| Minesoft (PatBase) | Search quality is gated on full-text ingest correctness, not on another frontend. | info@minesoft.com |
| LexisNexis Intellectual Property (TotalPatent, IPlytics) | Legal research + SEP/standards analytics both sit on full text. | Sales via LexisNexis IP |
| Cipher / Aistemos | Portfolio analytics needs stable CPC and claims text more than another crawler. | Corporate site |
| IP.com | Prior-art and professional search is a direct consumer of this schema. | Corporate site |

## Legal-AI

| Company | Why an acquisition lands | Public entry |
| --- | --- | --- |
| Harvey | Patent practice in 2,400+ legal orgs needs a rights-labeled, locally hostable USPTO corpus rather than scraping. | [Partnerships](https://www.harvey.ai/platform/partnerships) |
| Thomson Reuters (CoCounsel / Westlaw) | Existing legal AI plus IP content; missing piece is often the engineering of weekly XML, not another LLM wrapper. | Corporate development |
| Lexis+ AI | Same shape as TR: distribution exists, USPTO full-text plumbing is a DE tax. | Corporate development |
| Luminance | Document intelligence firms expand into patents only after the corpus is boring. | info@luminance.com |
| Spellbook | Contract AI moving toward patent prosecution support. | Public site / sales form |
| EvenUp, Relativity, Everlaw, DISCO, vLex | Litigation and discovery tools that want patent exhibits and prior art as first-class data. | Corporate sites |
| Legora, Paxton, Robin AI | Newer legal-AI stacks that should buy a corpus instead of hiring a USPTO XML team. | Corporate sites |

## Prior-art / search vendors

| Company | Why an acquisition lands | Public entry |
| --- | --- | --- |
| IPRally | Graph/AI prior-art search is only as good as normalized claims and CPC. | sales@iprally.com |
| Amplified | Dedicated prior-art search; ingest is a cost center. | info@amplified.ai |
| Ambercite, Patentics, Specifio, PQAI | Citation and search specialists. PQAI in particular is an open prior-art effort that benefits from a stable bulk layer. | Corporate sites |
| Google Patents | Unlikely acquirer; still a distribution benchmark. | n/a |

## Scientific-information companies

| Company | Why an acquisition lands | Public entry |
| --- | --- | --- |
| Digital Science (Dimensions) | Dimensions already blends grants, publications, and patents. A trustworthy USPTO full-text store is the missing local copy. | info@digital-science.com |
| Elsevier (Scopus, SciVal) | Patent–paper linkage products need the same claims/description text PatentPulse already normalized. | Corporate development |
| Clarivate (Web of Science / Derwent overlap) | See patent intelligence. | IP contact page |
| CAS (American Chemical Society) | Chemistry patents are a first-class CAS product; weekly XML plumbing is still DE. | Corporate site |
| Allen Institute for AI / Semantic Scholar | Open scientific indexers that treat patents as scholarly documents. | allenai.org |
| IEEE, ACS publications groups | Standards and society publishers with adjacent patent landscapes. | Corporate sites |

## AI-data companies

| Company | Why an acquisition lands | Public entry |
| --- | --- | --- |
| Hugging Face | Already hosts the snapshot. An acquisition is the pipeline, the weekly refresh, and the rights-aware exporter, not the Parquet files alone. | [Contact sales](https://huggingface.co/contact/sales), website@huggingface.co |
| Snorkel AI | Programmatic labeling over noisy XML is exactly what they sell; a clean USPTO base dataset shortens every patent vertical engagement. | info@snorkel.ai |
| Scale AI, Surge, Labelbox | Patent annotation programs start with a stable document store. | Corporate sales |
| Databricks / Mosaic | Enterprise customers ask for domain corpora; USPTO full text is a recurring request. | Corporate development |
| Cohere, Together AI, AI2 | Domain-continued pretraining on patents needs a legal-to-train, deduplicated dump rather than raw Red Book ZIPs. | Cohere partner form; Together AI sales; Ai2 |
| Gretel, Common Crawl-adjacent data firms | Synthetic or web-scale data companies that want a high-signal technical vertical. | Corporate sites |

## Disqualified or weak fits

- Pure docketing SaaS with no data platform team
- Firms that need EPO/WIPO/CN/JP first (this corpus is USPTO only)
- Buyers who require drawings, sequence listings as structured data, or PAIR prosecution histories (not in this snapshot)
