# Transfer plan — PatentPulse

**Date:** 2026-09-21  
**Status:** Operational checklist for closing. Not a legal agreement.

## Pre-close

1. Freeze Acquisition Release tag and Hub snapshot digest (see `ACQUISITION_RELEASE.md`).
2. Deliver data room under `docs/acquisition/` plus measured metrics JSON.
3. Confirm Hub dataset card / viewer config (`HUB_VIEWER_FIX.md`).
4. Inventory secrets: USPTO ODP key, Hugging Face write token — **rotate after close**.
5. Confirm `DATA_LICENSE.md` and USPTO redistribution constraints with counsel.

## Closing deliverables (typical)

| Deliverable | Location / action |
| --- | --- |
| GitHub repository transfer or exclusive license | GitHub settings / SPA |
| Hugging Face dataset ownership / collaborator transfer | Hub settings |
| Trademark / brand assets | `assets/` — registration status UNKNOWN |
| Domain / Pages (if any) | N/A unless buyer adds |
| Commercial pipeline customers | None claimed in-repo |

## Post-close

1. Buyer rotates all ingest/publish credentials.
2. Seller removes write access to Hub and GitHub after agreed handoff window.
3. Support window (if any) per commercial side letter — none implied by this file.

## Exclusions

- USPTO does not transfer with the deal.
- Historical open-source recipients keep rights only to historical copies.
- No fabricated customer list or revenue schedule is part of this plan.
