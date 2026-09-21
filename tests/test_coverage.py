"""Tests for coverage reporting (calendar estimate path, no API key)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from patentpulse.coverage import (
    build_coverage_report,
    calendar_expected_filenames,
    iter_weekday_dates,
)
from patentpulse.manifest import FileEntry, IngestManifest


def test_iter_weekday_dates_tuesdays():
    days = iter_weekday_dates(date(2018, 1, 1), date(2018, 1, 31), weekday=1)
    assert days[0] == date(2018, 1, 2)
    assert all(d.weekday() == 1 for d in days)


def test_calendar_expected_filenames_include_grant_and_app_patterns():
    expected = calendar_expected_filenames(date(2018, 1, 1), date(2018, 1, 14))
    assert any(name.startswith("ipg") for name in expected["grant_fulltext"])
    assert any(name.startswith("ipa") for name in expected["application_fulltext"])


def test_coverage_report_counts_missing_against_manifest(tmp_path: Path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    expected = calendar_expected_filenames(date(2018, 1, 1), date(2018, 1, 14))
    first_grant = expected["grant_fulltext"][0]
    manifest = IngestManifest(
        files={
            first_grant: FileEntry(
                path=f"/tmp/{first_grant}",
                status="complete",
                records_parsed=10,
                records_written=10,
            )
        }
    )
    manifest.save(data_root / "manifest.json")

    report = build_coverage_report(
        data_root=data_root,
        from_date=date(2018, 1, 1),
        to_date=date(2018, 1, 14),
        api_key=None,
    )
    assert report["expectation_source"] == "calendar_estimate"
    assert report["totals"]["expected_archives"] == (
        len(expected["grant_fulltext"]) + len(expected["application_fulltext"])
    )
    assert report["totals"]["complete_in_window"] == 1
    assert report["totals"]["missing_archives"] == report["totals"]["expected_archives"] - 1
    assert report["frozen_snapshot_reminder"]["unique_records"] == 5_929_464
