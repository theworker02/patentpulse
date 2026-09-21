#!/usr/bin/env bash
# Automate Track A of the historical corpus finish procedure.
# Requires USPTO_API_KEY. Safe to re-run; completed weeks are skipped.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FROM_DATE="2018-01-01"
WEEKS_PER_BATCH=20
MAX_BATCHES=100
DATA_ROOT="data"
SOURCE="both"

usage() {
  cat <<'EOF'
Usage: ./scripts/finish_corpus.sh [options]

  --from-date YYYY-MM-DD   Backfill window start (default: 2018-01-01)
  --weeks-per-batch N      Weeks per ingest sync invocation (default: 20)
  --max-batches N          Safety cap on sync loops (default: 100)
  --data-root PATH         PatentPulse data root (default: data)
  --source grant|application|both   (default: both)
  -h, --help               Show help

Environment:
  USPTO_API_KEY            Required Open Data Portal key
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-date) FROM_DATE="$2"; shift 2 ;;
    --weeks-per-batch) WEEKS_PER_BATCH="$2"; shift 2 ;;
    --max-batches) MAX_BATCHES="$2"; shift 2 ;;
    --data-root) DATA_ROOT="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "${USPTO_API_KEY:-}" ]]; then
  echo "USPTO_API_KEY is required. Register at https://data.uspto.gov/apis/getting-started" >&2
  exit 1
fi

REPORT_DIR="$ROOT/docs/acquisition/metrics"
mkdir -p "$REPORT_DIR"
REPORT_PATH="$REPORT_DIR/coverage_report.json"

echo "==> PatentPulse finish_corpus (Acquisition Release 1.0 Track A)"
echo "    from=$FROM_DATE weeks_per_batch=$WEEKS_PER_BATCH source=$SOURCE"

python -m patentpulse.coverage \
  --data-root "$DATA_ROOT" \
  --from-date "$FROM_DATE" \
  --json "$REPORT_PATH"

missing="$(python - <<PY
import json
print(json.load(open("$REPORT_PATH"))["totals"]["missing_archives"])
PY
)"

echo "Missing archives at start: $missing"
if [[ "$missing" == "0" ]]; then
  echo "Nothing to finish. Coverage is complete for the reported window."
  exit 0
fi

batch=1
while [[ "$batch" -le "$MAX_BATCHES" ]]; do
  echo "==> Sync batch $batch / $MAX_BATCHES (up to $WEEKS_PER_BATCH weeks)"
  python -m patentpulse.ingest --data-root "$DATA_ROOT" sync \
    --source "$SOURCE" \
    --format both \
    --weeks "$WEEKS_PER_BATCH"

  python -m patentpulse.coverage \
    --data-root "$DATA_ROOT" \
    --from-date "$FROM_DATE" \
    --json "$REPORT_PATH"

  missing="$(python - <<PY
import json
print(json.load(open("$REPORT_PATH"))["totals"]["missing_archives"])
PY
)"
  echo "Missing archives after batch $batch: $missing"
  if [[ "$missing" == "0" ]]; then
    echo "Coverage complete for window starting $FROM_DATE."
    python -m patentpulse.ingest --data-root "$DATA_ROOT" status || true
    exit 0
  fi
  batch=$((batch + 1))
done

echo "Reached --max-batches=$MAX_BATCHES with $missing archives still missing." >&2
echo "Inspect $REPORT_PATH and re-run; failed weeks appear in ingest status." >&2
exit 1
