# Security Policy — PatentPulse

## Supported versions

Security fixes are applied to the current `main` branch and the latest Acquisition Release tag. Older historical open-source copies are not patched under the proprietary license.

## Reporting a vulnerability

Do **not** open a public issue with exploit details.

1. Contact GitHub [@theworker02](https://github.com/theworker02) privately.
2. Include: affected path/module, impact, reproduction steps, and whether USPTO credentials or Hub tokens were involved.
3. Allow a reasonable window for triage before public disclosure.

## Scope notes for diligence

| Surface | Posture |
| --- | --- |
| Pipeline code | Local-first; no default telemetry |
| USPTO Open Data Portal key | Operator secret — never commit; rotate on transfer |
| Hugging Face token | Operator secret for publish only |
| Published Parquet | Public dataset; contains USPTO-originated text (not secrets) |
| SQLite / JSONL local stores | Buyer-controlled filesystem |

See [`docs/acquisition/SECURITY_POSTURE.md`](docs/acquisition/SECURITY_POSTURE.md) for the acquisition security posture summary.
