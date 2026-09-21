#!/usr/bin/env python3
"""Buyer evaluation demo: USPTO source → ingest → query → Parquet export.

Designed for a private evaluation clone. Uses the in-repo synthetic USPTO-style
fixture (not the multi-terabyte corpus). Target wall time: under 10 minutes.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from patentpulse.hf_release import build_release, validate_release
from patentpulse.ingest import init_workspace, run_local_ingest
from patentpulse.manifest import IngestManifest


def _step(title: str) -> float:
    print()
    print(f"==> {title}")
    return time.perf_counter()


def _done(started: float) -> float:
    elapsed = time.perf_counter() - started
    print(f"    done in {elapsed:.2f}s")
    return elapsed


def run_demo(*, keep_dir: Path | None = None) -> int:
    overall = time.perf_counter()
    timings: dict[str, float] = {}

    if keep_dir is not None:
        demo_root = keep_dir
        if demo_root.exists():
            shutil.rmtree(demo_root)
        demo_root.mkdir(parents=True, exist_ok=True)
    else:
        demo_root = Path(tempfile.mkdtemp(prefix="patentpulse-buyer-demo-"))

    data_root = demo_root / "data"
    release_dir = demo_root / "release"
    print("PatentPulse buyer demo (Acquisition Release 1.0)")
    print(f"Workspace: {demo_root}")

    t0 = _step("1/5 USPTO source — seed official-shaped weekly XML fixture")
    init_workspace(data_root)
    fixture = ROOT / "tests" / "fixtures" / "sample_bulk.xml"
    source = data_root / "raw" / "grants" / "demo_ipg180619.xml"
    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture, source)
    # Remove bootstrap duplicate so the demo shows a single clear source path.
    bootstrap = data_root / "raw" / "bootstrap_sample_bulk.xml"
    if bootstrap.exists():
        bootstrap.unlink()
    print(f"    source: {source} ({source.stat().st_size} bytes)")
    timings["source"] = _done(t0)

    t0 = _step("2/5 Ingestion — stream parse into SQLite + JSONL + manifest")
    stats = run_local_ingest(data_root=data_root, output_format="both")
    print(
        f"    parsed={stats['documents_parsed']} written={stats['records_written']} "
        f"failed={stats['documents_failed']}"
    )
    if stats["records_written"] < 1:
        print("Demo failed: no records written", file=sys.stderr)
        return 1
    timings["ingest"] = _done(t0)

    t0 = _step("3/5 Normalized record — inspect one JSONL row")
    jsonl_path = data_root / "processed" / "patents.jsonl"
    record = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    preview = {
        "patent_grant_id": record.get("patent_grant_id"),
        "publication_date": record.get("publication_date"),
        "invention_title": record.get("invention_title") or record.get("title"),
        "main_cpc_label": record.get("main_cpc_label"),
        "document_type": record.get("document_type"),
        "source_file": record.get("source_file"),
    }
    print(json.dumps(preview, indent=2))
    timings["inspect"] = _done(t0)

    t0 = _step("4/5 Query / search — SQLite CPC + title lookup")
    db_path = data_root / "processed" / "patents.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = conn.execute(
        """
        SELECT p.patent_grant_id, p.invention_title, c.cpc_code
        FROM patents AS p
        JOIN patent_cpc AS c ON c.patent_id = p.id
        WHERE c.cpc_code LIKE 'G06%'
        ORDER BY p.publication_date DESC
        LIMIT 5
        """
    ).fetchall()
    conn.close()
    if not rows:
        print("Demo failed: CPC query returned no rows", file=sys.stderr)
        return 1
    for row in rows:
        print(f"    {row[0]} | {row[2]} | {row[1]}")
    timings["query"] = _done(t0)

    t0 = _step("5/5 Parquet / HF export — immutable release + validate")
    # Exporter requires every manifest entry complete (true after successful ingest).
    manifest = IngestManifest.load(data_root / "manifest.json")
    incomplete = [e for e in manifest.files.values() if e.status != "complete"]
    if incomplete:
        print(
            f"Demo failed: manifest incomplete ({len(incomplete)} entries)",
            file=sys.stderr,
        )
        return 1
    summary = build_release(
        jsonl_path,
        release_dir,
        data_root=data_root,
        skip_invalid_json=True,
    )
    validate_release(release_dir)
    print(
        f"    records={summary.records_written} shards={sum(summary.shards_by_split.values())} "
        f"digest={summary.canonical_sha256[:16]}…"
    )
    timings["export"] = _done(t0)

    total = time.perf_counter() - overall
    print()
    print("Buyer demo complete")
    print("=" * 40)
    for name, seconds in timings.items():
        print(f"  {name:<8} {seconds:7.2f}s")
    print(f"  {'total':<8} {total:7.2f}s")
    print(f"Artifacts under: {demo_root}")
    if total > 600:
        print(
            "WARNING: exceeded 10-minute target on this host.",
            file=sys.stderr,
        )
        return 2
    print("PASS: under 10-minute evaluation budget.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-dir",
        type=Path,
        default=None,
        help="Persist demo workspace to this directory instead of a temp dir.",
    )
    args = parser.parse_args(argv)
    try:
        return run_demo(keep_dir=args.keep_dir)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"Buyer demo failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
