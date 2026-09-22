# Acquisition readiness report — PatentPulse

**Date:** 2026-09-21  
**No numeric score.** Statuses reflect in-repo evidence.

| Section | Status | Notes |
| --- | --- | --- |
| BUILD | READY_WITH_DISCLOSURE | Pipeline runnable; full corpus needs disk + USPTO key |
| TESTS | READY_WITH_DISCLOSURE | `pytest` + `scripts/buyer_demo.py`; CI workflow added |
| SECRETS | READY_WITH_DISCLOSURE | No production secrets in tree expected |
| DOCUMENTATION | READY_WITH_DISCLOSURE | Strong metrics/outreach room; legal pack expanded this program |
| IP OWNERSHIP | REQUIRES_LEGAL_REVIEW | Code vs USPTO text; license transition |
| LICENSE CLARITY | READY_WITH_DISCLOSURE | Current LICENSE clear; history documented without invented SHAs |
| DEPENDENCIES | READY_WITH_DISCLOSURE | See requirements.txt |
| DATA RIGHTS | REQUIRES_LEGAL_REVIEW | USPTO-derived corpus + Hub redistribution |
| REPRODUCIBILITY | READY_WITH_DISCLOSURE | Buyer demo + Hub snapshot digest |
| TRANSFERABILITY | READY_WITH_DISCLOSURE | See TRANSFER_PLAN.md |
| BUYER DEMO | READY_WITH_DISCLOSURE | Hub path hours; pipeline path days |
| KNOWN LIABILITIES | READY_WITH_DISCLOSURE | Bibliographic null cluster; Hub viewer fix; weekly catalog finish |

## Blockers

### Before outreach
- Root `ACQUISITION.md` (done this program)
- Hub empty-split viewer fix still operator-side (`HUB_VIEWER_FIX.md`)

### Before diligence
- Counsel review of USPTO data rights + license transition
- Formal waiver or Track B plan for 60.29% bibliographic cluster (`DISCLOSURE_SCHEDULE.md`)

### Before signing
- Formal IP assignment / SPA schedules
- Hub + GitHub transfer mechanics

### Before closing
- Credential rotation
- Confirm snapshot digest and release tag immutability
