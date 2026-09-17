"""Tests for ingestion orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from patentpulse import ingest
from patentpulse.ingest import init_workspace, remove_raw_archive_after_ingest, run_local_ingest


def test_init_and_run_local_ingest(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "raw" / "bootstrap_sample_bulk.xml").unlink(missing_ok=True)
    fixture = (
        Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_bulk.xml"
    )
    target = tmp_path / "raw" / "sample_bulk.xml"
    target.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    totals = run_local_ingest(data_root=tmp_path, output_format="sqlite")
    assert totals["files_processed"] == 1
    assert totals["documents_parsed"] == 2
    assert totals["records_written"] == 2
    assert (tmp_path / "processed" / "patents.db").exists()


def test_remove_raw_archive_retries_windows_file_lock(tmp_path: Path):
    archive = tmp_path / "weekly.zip"
    attempts = 0

    def locked_then_removed(_path: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("archive is temporarily locked")

    with (
        patch.object(Path, "unlink", autospec=True, side_effect=locked_then_removed),
        patch.object(ingest.time, "sleep") as sleep,
    ):
        assert remove_raw_archive_after_ingest(archive) is True

    assert attempts == 3
    assert sleep.call_count == 2
