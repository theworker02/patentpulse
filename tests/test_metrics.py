"""Tests for acquisition-grade quality, size, and throughput measurements."""

from __future__ import annotations

from pathlib import Path

from patentpulse.metrics import (
    benchmark_ingestion,
    corpus_inventory,
    extract_records_from_bulk,
    fixture_path,
    materialize_benchmark_xml,
    quality_from_records,
    summarize_release_errors,
    uniquify_document,
)


def test_uniquify_document_changes_grant_and_application_ids():
    original = fixture_path().read_text(encoding="utf-8")
    first = original.split("<?xml", 2)[1]
    first = "<?xml" + first
    updated = uniquify_document(first, 42)
    assert "<doc-number>10000042</doc-number>" in updated
    assert "<doc-number>15000042</doc-number>" in updated
    assert "<doc-number>10000000</doc-number>" not in updated


def test_materialize_and_quality_on_unique_fixture(tmp_path: Path):
    bulk = tmp_path / "bulk.xml"
    meta = materialize_benchmark_xml(bulk, documents=6)
    assert meta["unique_identities"] == 6
    records = [
        record
        for record in extract_records_from_bulk(bulk)
        if record.document_type != "unknown"
    ]
    assert len(records) == 6
    quality = quality_from_records(records)
    assert quality["records"] == 6
    assert quality["unique_record_keys"] == 6
    assert quality["fill_rates"]["invention_title"] == 1.0
    assert quality["fill_rates"]["abstract_text"] == 1.0
    assert quality["fill_rates"]["claims_text"] == 1.0
    assert quality["alias_consistency_rate"] == 1.0
    assert quality["iso_publication_date_rate"] == 1.0
    assert quality["boilerplate_leak_rate"] == 0.0


def test_mixed_bulk_counts_unknown_and_duplicate_identities(tmp_path: Path):
    bulk = tmp_path / "mixed.xml"
    meta = materialize_benchmark_xml(
        bulk,
        documents=10,
        unknown_documents=2,
        truncated_documents=1,
        duplicate_fraction=0.2,
    )
    assert meta["duplicate_identities"] == 2
    assert meta["unknown_documents"] == 2
    text = bulk.read_text(encoding="utf-8")
    assert "sequence-cwu" in text
    assert "<invention-title>Broken" in text


def test_summarize_release_errors_matches_published_identity_math():
    manifest = {
        "source_file": "patents.jsonl",
        "source_bytes": 873811406212,
        "records_seen": 6500178,
        "records_written": 5929464,
        "duplicates_skipped": 570714,
        "invalid_json_rows": [{"line": 1, "error": "Expecting value"}] * 186,
        "records_by_split": {"train": 1, "validation": 1, "test": 1},
        "shards_by_split": {"train": 1},
        "canonical_sha256": "abc",
        "created_at": "2026-08-28T03:13:23+00:00",
    }
    summary = summarize_release_errors(manifest)
    assert summary["identity_check_seen_minus_duplicates_equals_written"] is True
    assert summary["invalid_json_rows"] == 186
    assert round(summary["duplicate_rate_of_valid_json"], 6) == round(570714 / 6500178, 6)
    assert summary["invalid_json_by_reason"] == {"Expecting value": 186}


def test_corpus_inventory_ratios(tmp_path: Path):
    manifest = {
        "source_bytes": 1000,
        "records_written": 10,
    }
    tree = [
        {"type": "file", "path": "data/train/part-00000.parquet", "size": 250},
        {"type": "file", "path": "README.md", "size": 50},
    ]
    parquet = {
        "column_chunk_uncompressed_bytes": 800,
        "column_chunk_compressed_bytes": 200,
    }
    inventory = corpus_inventory(manifest=manifest, tree=tree, parquet=parquet)
    assert inventory["published_parquet_file_bytes"] == 250
    assert inventory["jsonl_to_parquet_file_ratio"] == 0.25
    assert inventory["parquet_page_compression_ratio"] == 0.25
    assert inventory["jsonl_bytes_per_unique_record"] == 100.0


def test_benchmark_ingestion_reports_throughput_and_replay_dedup(tmp_path: Path):
    report = benchmark_ingestion(
        documents=8,
        work_dir=tmp_path / "work",
        unknown_documents=2,
        truncated_documents=1,
        duplicate_fraction=0.25,
    )
    assert report["unique_pass"]["documents_parsed"] == 8
    assert report["unique_pass"]["records_written"] == 8
    assert report["unique_pass"]["docs_per_second"] > 0
    assert report["replay_pass"]["expected_all_skipped"] is True
    assert report["mixed_pass"]["documents_failed"] >= 2
    assert report["fixture_quality_sample"]["records"] == 8
