# Disclosure schedule — PatentPulse

**Date:** 2026-09-21  
**Status:** Diligence disclosures. Not an admission of liability.

## Material known limitations

1. **Bibliographic null cluster (~60.29%)**  
   Fields such as `kind_code`, `filing_date`, inventor names, and related extras show ~60.29% fill on the **published** 5.93M snapshot. Per [`QUALITY_METRICS.md`](QUALITY_METRICS.md), this is a **schema-evolution gap** (columns added after part of append-only JSONL was written), not random corruption. Core IDs, claims, dates, and document type remain at **100%** fill.  
   **Buyer options:** (a) accept as-is with this disclosure; (b) re-extract historical weeks (Track B) using the current parser; (c) treat affected columns as best-effort until rebuilt.

2. **Weekly catalog ≠ snapshot completeness**  
   The published Parquet snapshot is not a claim that every USPTO weekly ZIP in 2018–present is `complete` in an operator manifest. Residual coverage is finished via [`CORPUS_FINISH.md`](CORPUS_FINISH.md).

3. **Hub dataset viewer**  
   Empty `unspecified` split can break the Hub preview UI until [`HUB_VIEWER_FIX.md`](HUB_VIEWER_FIX.md) is applied on the live card.

4. **License transition**  
   Historical public copies may remain under prior open terms; current tree is proprietary source-available. See `LICENSE_TRANSITION_NOTICE.md` and `LICENSE_HISTORY.md`.

5. **Data rights**  
   USPTO-originated patent text is not sold as seller-owned literature; redistribution follows `DATA_LICENSE.md` and applicable law.

6. **Single maintainer / short commercial history**  
   No fabricated revenue, MAU, or customer logos are offered.

## Explicit non-claims

- Not legal advice, patentability, validity, or infringement analysis.
- Fixture ingest throughput ≠ full-text production throughput.
- No asking price in-repo.
