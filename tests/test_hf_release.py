"""Tests for the stable Parquet release workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from patentpulse.hf_release import (
    ReleaseError,
    ReleaseReadinessError,
    ReleaseValidationError,
    assert_manifest_complete,
    build_release,
    dataset_card_data_files,
    normalize_record,
    release_record_key,
    validate_release,
)
from patentpulse.manifest import FileEntry, IngestManifest


def test_normalize_record_upgrades_legacy_shape_and_removes_local_path():
    record = normalize_record(
        {
            "patent_grant_id": "10000000",
            "publication_date": "2024-06-01",
            "invention_title": "Legacy title",
            "abstract_text": "Legacy abstract",
            "claims_text": "Legacy claims",
            "description_text": "Legacy description",
            "primary_cpc_codes": ["G06F16/245"],
            "document_type": "grant",
            "source_file": r"C:\\Users\\example\\data\\raw\\ipg240601.zip",
        }
    )
    assert record["title"] == "Legacy title"
    assert record["abstract"] == record["abstract_text"]
    assert record["cpc_labels"] == ["G06F16/245"]
    assert record["source_file"] == "ipg240601.zip"
    assert record["inventor_list"] == []
    assert release_record_key(record) == release_record_key(dict(record))


def test_build_and_validate_release_with_mixed_historical_rows(tmp_path: Path):
    input_path = tmp_path / "patents.jsonl"
    rows = [
        {
            "patent_grant_id": "10000000",
            "publication_date": "2024-06-01",
            "invention_title": "Legacy",
            "abstract_text": "A",
            "claims_text": "B",
            "description_text": "C",
            "primary_cpc_codes": ["G06F16/245"],
            "document_type": "grant",
            "source_file": r"C:\\workspace\\ipg240601.zip",
        },
        {
            "patent_grant_id": "10000001",
            "publication_date": "2025-01-01",
            "invention_title": "Current",
            "abstract_text": "D",
            "claims_text": "E",
            "description_text": "F",
            "primary_cpc_codes": ["G06N20/00"],
            "cpc_labels": ["G06N20/00"],
            "document_type": "application",
            "source_file": "data/raw/ipa250101.zip",
            "inventor_list": [{"inventor_name_last": "Chen", "inventor_name_first": "A"}],
        },
        {
            "patent_number": "10000002",
            "date_published": "2026-01-01",
            "title": "Alias only",
            "abstract": "G",
            "claims": "H",
            "full_description": "I",
            "main_cpc_label": "H04L9/00",
            "document_type": "grant",
            "source_file": "/home/example/ipg260101.zip",
        },
        {
            "patent_grant_id": "10000000",
            "publication_date": "2024-06-01",
            "invention_title": "Legacy retry",
            "abstract_text": "A",
            "claims_text": "B",
            "description_text": "C",
            "document_type": "grant",
            "source_file": r"C:\\retry\\ipg240601.zip",
        },
    ]
    input_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    output = tmp_path / "release"

    summary = build_release(
        input_path,
        output,
        max_shard_bytes=1_000_000,
        row_group_bytes=100,
        max_records=None,
    )

    assert summary.records_seen == 4
    assert summary.duplicates_skipped == 1
    assert summary.records_by_split == {"test": 1, "train": 1, "validation": 1}
    assert validate_release(output) == summary
    assert (output / "README.md").read_text(encoding="utf-8").startswith("---\n")
    assert "machine-learning research and training" in (output / "DATA_LICENSE.md").read_text(encoding="utf-8")


def test_incomplete_manifest_blocks_release(tmp_path: Path):
    manifest = IngestManifest(files={"source": FileEntry(path="source.zip", status="running")})
    manifest.save(tmp_path / "manifest.json")
    with pytest.raises(ReleaseReadinessError, match="not complete"):
        assert_manifest_complete(tmp_path)


def test_export_requires_explicit_opt_in_to_skip_malformed_json(tmp_path: Path):
    input_path = tmp_path / "patents.jsonl"
    input_path.write_text(
        '{"patent_grant_id":"10000000","publication_date":"2024-01-01","document_type":"grant"}\n'
        'not-json\n',
        encoding="utf-8",
    )
    with pytest.raises(ReleaseValidationError, match="Invalid JSON"):
        build_release(input_path, tmp_path / "strict")

    summary = build_release(input_path, tmp_path / "repaired", skip_invalid_json=True)
    assert summary.records_written == 1
    assert summary.invalid_json_rows == [{"line": 2, "error": "Expecting value"}]


def test_export_can_record_invalid_utf8_when_explicitly_enabled(tmp_path: Path):
    input_path = tmp_path / "patents.jsonl"
    input_path.write_bytes(
        b'{"patent_grant_id":"10000000","publication_date":"2024-01-01","document_type":"grant"}\n'
        b'{"patent_grant_id":"bad\x89"}\n'
    )
    with pytest.raises(ReleaseValidationError, match="Invalid UTF-8"):
        build_release(input_path, tmp_path / "strict")

    summary = build_release(input_path, tmp_path / "repaired", skip_invalid_json=True)
    assert summary.records_written == 1
    assert summary.invalid_json_rows == [{"line": 2, "error": "Invalid UTF-8: invalid start byte"}]


def test_dataset_card_omits_empty_unspecified_split():
    yaml = dataset_card_data_files({"train": 10, "validation": 2, "test": 1})
    assert "path: data/train/*.parquet" in yaml
    assert "path: data/unspecified/*.parquet" not in yaml


def test_dataset_card_includes_unspecified_only_when_populated():
    yaml = dataset_card_data_files({"unspecified": 4})
    assert "path: data/unspecified/*.parquet" in yaml


def test_dataset_card_rejects_empty_release():
    with pytest.raises(ReleaseError, match="no split contains records"):
        dataset_card_data_files({})


def test_built_readme_does_not_advertise_missing_unspecified_glob(tmp_path: Path):
    input_path = tmp_path / "patents.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "patent_grant_id": "10000000",
                "publication_date": "2024-06-01",
                "document_type": "grant",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = build_release(input_path, tmp_path / "release", max_shard_bytes=1_000_000, row_group_bytes=100)
    readme = (tmp_path / "release" / "README.md").read_text(encoding="utf-8")
    assert "path: data/train/*.parquet" in readme
    assert "path: data/unspecified/*.parquet" not in readme
    assert summary.records_by_split == {"train": 1}
