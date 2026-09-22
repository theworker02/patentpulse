# License history — PatentPulse

**Date:** 2026-09-21  
**Status:** Diligence aid. Confirm SHAs against `git log` before relying in a binding schedule.

## Current terms

| Item | Value |
| --- | --- |
| Code license | Proprietary source-available — [`LICENSE`](../../LICENSE) |
| Commercial path | [`COMMERCIAL.md`](../../COMMERCIAL.md) |
| Data / USPTO-derived text | [`DATA_LICENSE.md`](../../DATA_LICENSE.md) — **not** MIT for patent document bodies |
| Transition letter | [`LICENSE_TRANSITION_NOTICE.md`](../../LICENSE_TRANSITION_NOTICE.md) |

## Historical note

Public distributions of this project previously used a permissive open-source style license (referenced as MIT in [`ASSET_SCHEDULE.md`](ASSET_SCHEDULE.md) for earlier packaging). The repository has since transitioned to proprietary source-available terms so commercial licenses and acquisition/IP transfer are possible.

**Important:** This file does **not** invent a specific transition commit SHA if git history on the buyer’s clone does not clearly label it. Diligence should:

1. `git log -- LICENSE NOTICE LICENSE_TRANSITION_NOTICE.md`
2. Inspect the earliest tagged release artifacts retained by the seller
3. Schedule any historical MIT (or other) grants as **non-exclusive survivors** for those historical copies only

## Practical buyer takeaway

- **Buy/license current `main`:** proprietary evaluation + commercial license / SPA path.
- **Someone already has an old MIT tarball:** that tarball’s terms still govern **that copy**; they do not receive ongoing proprietary updates under MIT.
