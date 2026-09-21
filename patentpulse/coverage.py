"""Catalog vs manifest coverage report for the historical USPTO backfill.

Compares expected weekly grant/application archives in a date window against
``data/manifest.json``. With ``USPTO_API_KEY``, the USPTO Open Data Portal
listing is authoritative; without it, a Tuesday/Thursday calendar estimate is
used for planning only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from patentpulse.download import list_odp_product_files, resolve_api_key
from patentpulse.ingest import DEFAULT_DATA_ROOT
from patentpulse.manifest import IngestManifest
from patentpulse.sources import (
    APPLICATION_FULLTEXT,
    GRANT_FULLTEXT,
    application_zip_name,
    grant_zip_name,
)

DEFAULT_FROM = date(2018, 1, 1)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def iter_weekday_dates(start: date, end: date, *, weekday: int) -> list[date]:
    """Return dates with ``weekday`` (Mon=0 … Sun=6) in ``[start, end]``."""
    cursor = start
    while cursor.weekday() != weekday:
        cursor += timedelta(days=1)
        if cursor > end:
            return []
    out: list[date] = []
    while cursor <= end:
        out.append(cursor)
        cursor += timedelta(days=7)
    return out


def calendar_expected_filenames(start: date, end: date) -> dict[str, list[str]]:
    """Planning estimate: grants on Tuesday, applications on Thursday."""
    grants = [
        grant_zip_name(year=d.year, month=d.month, day=d.day)
        for d in iter_weekday_dates(start, end, weekday=1)
    ]
    applications = [
        application_zip_name(year=d.year, month=d.month, day=d.day)
        for d in iter_weekday_dates(start, end, weekday=3)
    ]
    return {"grant_fulltext": grants, "application_fulltext": applications}


def odp_expected_filenames(
    *,
    api_key: str,
    start: date,
    end: date,
) -> dict[str, list[str]]:
    """Authoritative expected set from the USPTO Open Data Portal catalog."""
    from_date = start.isoformat()
    to_date = end.isoformat()
    result: dict[str, list[str]] = {}
    for label, product in (
        ("grant_fulltext", GRANT_FULLTEXT.odp_product_id),
        ("application_fulltext", APPLICATION_FULLTEXT.odp_product_id),
    ):
        files = list_odp_product_files(
            product,
            api_key=api_key,
            from_date=from_date,
            to_date=to_date,
            limit=None,
        )
        names: list[str] = []
        for info in files or []:
            name = info.get("fileName") or info.get("file_name")
            if name:
                names.append(str(name))
        result[label] = sorted(set(names))
    return result


def manifest_complete_filenames(manifest: IngestManifest) -> set[str]:
    return {
        Path(entry.path).name
        for entry in manifest.files.values()
        if entry.status == "complete"
    }


def manifest_status_counts(manifest: IngestManifest) -> dict[str, int]:
    counts = {"complete": 0, "pending": 0, "running": 0, "failed": 0, "other": 0}
    for entry in manifest.files.values():
        if entry.status in counts:
            counts[entry.status] += 1
        else:
            counts["other"] += 1
    return counts


def build_coverage_report(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    from_date: date = DEFAULT_FROM,
    to_date: date | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    end = to_date or date.today()
    if end < from_date:
        raise ValueError("to_date must be on or after from_date")

    manifest = IngestManifest.load(data_root / "manifest.json")
    complete = manifest_complete_filenames(manifest)
    key = resolve_api_key(api_key)
    if key:
        source = "odp"
        expected = odp_expected_filenames(api_key=key, start=from_date, end=end)
    else:
        source = "calendar_estimate"
        expected = calendar_expected_filenames(from_date, end)

    products: dict[str, Any] = {}
    total_expected = 0
    total_missing = 0
    total_complete_in_window = 0
    for product, names in expected.items():
        missing = sorted(name for name in names if name not in complete)
        present = sorted(name for name in names if name in complete)
        products[product] = {
            "expected_archives": len(names),
            "complete_in_window": len(present),
            "missing_archives": len(missing),
            "missing_sample": missing[:25],
            "complete_sample": present[:10],
        }
        total_expected += len(names)
        total_missing += len(missing)
        total_complete_in_window += len(present)

    # Rough storage/compute planning for remaining weeks (see CORPUS_FINISH.md).
    avg_zip_gb = 1.5  # transient; deleted after ingest by default
    avg_docs_per_week = 8_000
    size_adjusted_docs_per_sec = 19.0
    remaining_parse_hours = (
        (total_missing * avg_docs_per_week) / size_adjusted_docs_per_sec / 3600.0
        if total_missing
        else 0.0
    )

    return {
        "generated_at": utc_now(),
        "data_root": str(data_root.resolve()),
        "window": {"from_date": from_date.isoformat(), "to_date": end.isoformat()},
        "expectation_source": source,
        "manifest_summary": manifest.summary(),
        "manifest_status_counts": manifest_status_counts(manifest),
        "products": products,
        "totals": {
            "expected_archives": total_expected,
            "complete_in_window": total_complete_in_window,
            "missing_archives": total_missing,
            "coverage_ratio": (
                round(total_complete_in_window / total_expected, 6)
                if total_expected
                else None
            ),
        },
        "resource_estimate_for_missing": {
            "notes": (
                "Planning figures only. Transient ZIP disk assumes ~1.5 GB/week "
                "resident; parse time uses ~19 docs/s size-adjusted single-process "
                "estimate from Acquisition Release 1.0 benchmarks. "
                "If this clone has an empty data/manifest.json (typical for a fresh "
                "git checkout), missing_archives equals the full calendar/ODP window "
                "even though the published Hub snapshot already contains 5.93M rows. "
                "Run coverage on the operator host that owns the production manifest."
            ),
            "transient_zip_gb_if_one_at_a_time": avg_zip_gb,
            "transient_zip_gb_if_all_retained": round(total_missing * avg_zip_gb, 1),
            "assumed_docs_per_missing_week": avg_docs_per_week,
            "estimated_parse_cpu_hours_single_process": round(remaining_parse_hours, 2),
            "persistent_parquet_gb_current_snapshot": 211.41,
            "persistent_jsonl_gb_current_snapshot": 873.81,
        },
        "frozen_snapshot_reminder": {
            "unique_records": 5_929_464,
            "shards": 44,
            "publication_years": "2018-2026",
            "canonical_digest": (
                "42d3a4ae94b40d7e0ba3d76e02ce8af92704adde242153389b3d7cef544e4944"
            ),
        },
        "next_commands": [
            "export USPTO_API_KEY=...",
            "python -m patentpulse.ingest sync --source both --format both --weeks 20",
            "python -m patentpulse.coverage --from-date 2018-01-01 --json docs/acquisition/metrics/coverage_report.json",
            "./scripts/finish_corpus.sh --from-date 2018-01-01 --weeks-per-batch 20",
        ],
    }


def print_report(report: dict[str, Any]) -> None:
    totals = report["totals"]
    print("PatentPulse coverage report")
    print("=" * 40)
    print(f"Window:     {report['window']['from_date']} → {report['window']['to_date']}")
    print(f"Source:     {report['expectation_source']}")
    print(f"Expected:   {totals['expected_archives']}")
    print(f"Complete:   {totals['complete_in_window']}")
    print(f"Missing:    {totals['missing_archives']}")
    if totals["coverage_ratio"] is not None:
        print(f"Coverage:   {100.0 * totals['coverage_ratio']:.2f}%")
    print()
    for product, stats in report["products"].items():
        print(
            f"{product}: expected={stats['expected_archives']} "
            f"complete={stats['complete_in_window']} missing={stats['missing_archives']}"
        )
        if stats["missing_sample"]:
            print(f"  missing sample: {', '.join(stats['missing_sample'][:8])}")
    estimate = report["resource_estimate_for_missing"]
    print()
    print("Resource estimate for missing archives")
    print(
        f"  parse CPU hours (single process, planning): "
        f"{estimate['estimated_parse_cpu_hours_single_process']}"
    )
    print(
        f"  transient ZIP if all retained (planning GB): "
        f"{estimate['transient_zip_gb_if_all_retained']}"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report USPTO weekly archive coverage vs the local ingest manifest.",
    )
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--from-date", default="2018-01-01", help="YYYY-MM-DD")
    parser.add_argument("--to-date", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--api-key", default=None, help="USPTO ODP API key")
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path to write the machine-readable report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        report = build_coverage_report(
            data_root=args.data_root,
            from_date=_parse_date(args.from_date),
            to_date=_parse_date(args.to_date) if args.to_date else None,
            api_key=args.api_key,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"Coverage report failed: {exc}", file=sys.stderr)
        return 1
    print_report(report)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
