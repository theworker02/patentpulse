# Security posture — PatentPulse

**Date:** 2026-09-21  
**Status:** Diligence summary. Not a penetration-test report.

## Summary

PatentPulse is a **local data pipeline** plus a **published Hugging Face snapshot**. There is no multi-tenant SaaS control plane in this repository. The primary secrets are operator-supplied USPTO and Hub credentials used for ingest/publish, not application passwords.

## Trust boundaries

1. **Operator workstation** — runs `patentpulse.ingest`, holds API keys, writes SQLite/JSONL.
2. **USPTO bulk / ODP endpoints** — official source archives; TLS as provided by USPTO.
3. **Hugging Face Hub** — immutable Parquet release; public read for the published dataset.
4. **Buyer runtime** — after transfer, buyer owns keys, disk, and any downstream search/embedding services.

## Findings relevant to acquisition

| Item | Status |
| --- | --- |
| Secrets in git history | None expected for production keys; verify with buyer secret scan |
| Default network exfiltration | None — ingest only when operator runs sync |
| Dependency risk | Python stdlib-heavy core; optional `datasets` / `huggingface_hub` for Hub path |
| Supply chain | Pin or lock recommended before production buyer deploy |
| Dataset content | USPTO patent text — not personal consumer PII by design; still subject to applicable law |

## Recommendations before closing

- Rotate any USPTO ODP and Hugging Face tokens after SPA/APA signing.
- Run `pip-audit` / similar on the buyer environment.
- Confirm Hub dataset card and access controls match the intended public/private posture.
