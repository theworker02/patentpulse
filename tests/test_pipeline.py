"""Unit tests for the PatentPulse streaming extraction pipeline."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from patentpulse.clean import clean_patent_text
from patentpulse.extract import extract_patent_from_xml
from patentpulse.parse import parse_bulk_file
from patentpulse.stream import iter_concatenated_documents


FIXTURE = Path(__file__).parent / "fixtures" / "sample_bulk.xml"


def test_iter_concatenated_documents_splits_bulk_file():
    with FIXTURE.open("r", encoding="utf-8") as handle:
        documents = list(iter_concatenated_documents(handle))
    assert len(documents) == 2
    assert documents[0].startswith("<?xml")
    assert "</us-patent-grant>" in documents[0]
    assert "10000000" in documents[0]
    assert "10000001" in documents[1]


def test_extract_patent_fields_from_sample_document():
    with FIXTURE.open("r", encoding="utf-8") as handle:
        first_doc = next(iter_concatenated_documents(handle))

    record = extract_patent_from_xml(first_doc, source_file="sample_bulk.xml")

    assert record.patent_grant_id == "10000000"
    assert record.application_number == "15123456"
    assert record.publication_date == "2018-06-19"
    assert record.invention_title == "Coordinated multi-agent sensor fusion system"
    assert "sensor feeds" in (record.abstract_text or "")
    assert "LiDAR and IMU" in (record.description_text or "")
    assert "claim 1" in (record.claims_text or "").lower()
    assert record.primary_cpc_codes == ["G06F16/245"]
    assert record.further_cpc_codes == ["G06N20/00"]
    assert record.ipc_codes == ["G06F16/245"]
    assert record.kind_code == "B2"
    assert record.filing_date == "2016-05-01"
    assert record.application_type == "utility"
    assert record.claim_count == 2
    assert record.inventor_list[0].inventor_name_last == "Chen"
    assert record.assignee_names == ["Pulse Labs Inc."]
    assert record.examiner_name_last == "Nguyen"
    assert record.cited_patent_ids == ["US-5555555-A"]
    assert "Sensor Fusion Review" in record.npl_citations[0]
    assert record.related_application_numbers == ["14000000"]
    assert "LiDAR and IMU" in (record.summary or "")
    assert record.document_type == "grant"


def test_cleaning_strips_cross_reference_boilerplate():
    raw = (
        "CROSS-REFERENCE TO RELATED APPLICATIONS\n"
        "This application claims priority to provisional application 62/000,000.\n"
        "SUMMARY\n"
        "Embodiments fuse LiDAR and IMU streams."
    )
    cleaned = clean_patent_text(raw, strip_boilerplate=True)
    assert "CROSS-REFERENCE" not in cleaned
    assert "SUMMARY" in cleaned
    assert "LiDAR and IMU" in cleaned


def test_end_to_end_sqlite_and_jsonl(tmp_path: Path):
    db_path = tmp_path / "patents.db"
    jsonl_path = tmp_path / "patents.jsonl"

    stats = parse_bulk_file(
        FIXTURE,
        db_path,
        output_format="both",
        batch_size=10,
    )
    assert stats["documents_parsed"] == 2
    assert stats["records_written"] >= 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT patent_grant_id FROM patents ORDER BY patent_grant_id").fetchall()
    assert [row["patent_grant_id"] for row in rows] == ["10000000", "10000001"]

    cpc_rows = conn.execute(
        "SELECT cpc_code FROM patent_cpc ORDER BY cpc_code"
    ).fetchall()
    assert len(cpc_rows) >= 2
    conn.close()

    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    payload = json.loads(lines[0])
    assert payload["patent_grant_id"] == "10000000"
    assert payload["primary_cpc_codes"] == ["G06F16/245"]
    assert payload["title"] == payload["invention_title"]
    assert payload["cpc_labels"] == ["G06F16/245", "G06N20/00"]
    assert payload["cited_patent_ids"] == ["US-5555555-A"]
    assert payload["cited_patents"] == payload["cited_patent_ids"]
