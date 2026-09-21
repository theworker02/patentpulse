#!/usr/bin/env python3
"""Reproducible PatentPulse ingestion throughput benchmark.

Runs against the checked-in fixture (or a synthetic unique-ID expansion of it).
Writes JSON to stdout and optionally to --output.

Example:
  python scripts/benchmark_ingestion.py --docs 2000 --output docs/acquisition/metrics/ingestion_benchmark.json
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from patentpulse.extract import extract_patent_from_xml
from patentpulse.parse import parse_bulk_file
from patentpulse.stream import iter_concatenated_documents

FIXTURE = ROOT / "tests" / "fixtures" / "sample_bulk.xml"


def _build_unique_bulk(destination: Path, n_docs: int) -> int:
    """Write n_docs unique grant/application XML documents derived from the fixture."""
    templates = list(iter_concatenated_documents(FIXTURE.open("r", encoding="utf-8")))
    if not templates:
        raise RuntimeError(f"No documents found in fixture: {FIXTURE}")

    with destination.open("w", encoding="utf-8") as handle:
        for index in range(n_docs):
            text = templates[index % len(templates)]
            grant_id = 10_000_000 + index
            app_num = 15_000_000 + index
            text = text.replace("10000000", f"{grant_id:08d}").replace("10000001", f"{grant_id:08d}")
            text = text.replace("15123456", f"{app_num:08d}").replace("15123457", f"{app_num:08d}")
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
    return destination.stat().st_size


def _bench_extract(bulk_path: Path, bulk_bytes: int) -> dict:
    started = time.perf_counter()
    count = 0
    with bulk_path.open("r", encoding="utf-8") as handle:
        for document in iter_concatenated_documents(handle):
            extract_patent_from_xml(document, source_file="benchmark.xml")
            count += 1
    elapsed = time.perf_counter() - started
    return {
        "documents": count,
        "elapsed_s": round(elapsed, 4),
        "docs_per_s": round(count / elapsed, 2) if elapsed else None,
        "input_MB_per_s": round((bulk_bytes / 1e6) / elapsed, 3) if elapsed else None,
    }


def _bench_e2e(bulk_path: Path, bulk_bytes: int, batch_size: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "patents.db"
        started = time.perf_counter()
        stats = parse_bulk_file(
            bulk_path,
            db_path,
            output_format="both",
            batch_size=batch_size,
        )
        elapsed = time.perf_counter() - started
        jsonl_path = tmp_path / "patents.jsonl"
        return {
            **stats,
            "elapsed_s": round(elapsed, 4),
            "docs_per_s": round(stats["documents_parsed"] / elapsed, 2) if elapsed else None,
            "input_MB_per_s": round((bulk_bytes / 1e6) / elapsed, 3) if elapsed else None,
            "db_MB": round(db_path.stat().st_size / 1e6, 3),
            "jsonl_MB": round(jsonl_path.stat().st_size / 1e6, 3) if jsonl_path.exists() else 0.0,
            "batch_size": batch_size,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=int, default=2000, help="Synthetic unique documents to parse")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not FIXTURE.exists():
        raise SystemExit(f"Fixture missing: {FIXTURE}")

    with tempfile.TemporaryDirectory() as tmp:
        bulk_path = Path(tmp) / "benchmark_bulk.xml"
        bulk_bytes = _build_unique_bulk(bulk_path, args.docs)
        extract = _bench_extract(bulk_path, bulk_bytes)
        e2e = _bench_e2e(bulk_path, bulk_bytes, args.batch_size)

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "machine": platform.machine(),
            "processor": platform.processor() or platform.machine(),
        },
        "fixture": str(FIXTURE.relative_to(ROOT)),
        "input_bytes": bulk_bytes,
        "requested_docs": args.docs,
        "extract_only": extract,
        "e2e_sqlite_and_jsonl": e2e,
        "notes": [
            "Synthetic documents reuse fixture XML with unique grant/application identifiers so SQLite dedup does not collapse the workload.",
            "Throughput is CPU-bound XML parse + clean + write; network download of USPTO archives is excluded.",
            "Absolute docs/s depends on document size; fixture documents are small relative to full utility patents.",
        ],
    }
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
