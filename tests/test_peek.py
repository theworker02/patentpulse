"""Tests for patentpulse.peek helpers."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from patentpulse.peek import (
    PeekError,
    collect_stats,
    connect_readonly,
    get_patent,
    main,
    search_patents,
)
from patentpulse.schema import PATENTS_DDL, _ensure_columns


def _make_fixture_db(path: Path) -> Path:
    """Create a tiny patents.db matching production column names."""
    conn = sqlite3.connect(path)
    conn.executescript(PATENTS_DDL)
    _ensure_columns(conn)
    rows = [
        (
            "10000000",
            "15123456",
            "2018-06-19",
            "Coordinated multi-agent sensor fusion system",
            "A system that fuses sensor feeds from LiDAR and cameras.",
            "grant",
            "sample_bulk.xml",
        ),
        (
            "10000001",
            "16111222",
            "2019-01-15",
            "Distributed ledger for supply chain",
            "Methods for tracking goods with a blockchain ledger.",
            "grant",
            "sample_bulk.xml",
        ),
        (
            None,
            "US20200001111A1",
            "2020-01-02",
            "Neural network quantization application",
            "An application describing low-bit sensor fusion quantization.",
            "application",
            "app_sample.xml",
        ),
    ]
    for grant_id, app_no, pub_date, title, abstract, dtype, source in rows:
        conn.execute(
            """
            INSERT INTO patents (
                patent_grant_id, application_number, publication_date,
                invention_title, abstract_text, document_type, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (grant_id, app_no, pub_date, title, abstract, dtype, source),
        )
    patent_id = conn.execute(
        "SELECT id FROM patents WHERE patent_grant_id = '10000000'"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO patent_cpc (patent_id, cpc_code, is_primary, position) "
        "VALUES (?, 'G06F16/245', 1, 0)",
        (patent_id,),
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def peek_db(tmp_path: Path) -> Path:
    return _make_fixture_db(tmp_path / "patents.db")


def test_connect_readonly_missing_db(tmp_path: Path):
    missing = tmp_path / "nope.db"
    with pytest.raises(PeekError) as excinfo:
        connect_readonly(missing)
    message = str(excinfo.value)
    assert "not found" in message.lower()
    assert "ingest" in message.lower() or "load_dataset" in message


def test_collect_stats(peek_db: Path):
    conn = connect_readonly(peek_db)
    try:
        stats = collect_stats(conn)
    finally:
        conn.close()

    assert stats["patent_rows"] == 3
    assert stats["cpc_rows"] == 1
    assert stats["publication_date_min"] == "2018-06-19"
    assert stats["publication_date_max"] == "2020-01-02"
    assert stats["document_types"]["grant"] == 2
    assert stats["document_types"]["application"] == 1


def test_search_patents_like(peek_db: Path):
    conn = connect_readonly(peek_db)
    try:
        hits = search_patents(conn, "sensor fusion", limit=10)
    finally:
        conn.close()

    assert len(hits) >= 1
    titles = " ".join(h.get("invention_title") or "" for h in hits).lower()
    abstracts = " ".join(h.get("abstract_text") or "" for h in hits).lower()
    assert "sensor" in titles or "sensor" in abstracts


def test_search_respects_limit(peek_db: Path):
    conn = connect_readonly(peek_db)
    try:
        hits = search_patents(conn, "a", limit=1)
    finally:
        conn.close()
    assert len(hits) <= 1


def test_get_patent_by_grant_id(peek_db: Path):
    conn = connect_readonly(peek_db)
    try:
        record = get_patent(conn, "10000000")
    finally:
        conn.close()

    assert record is not None
    assert record["patent_grant_id"] == "10000000"
    assert record["invention_title"].startswith("Coordinated")
    assert record["cpc_codes"][0]["cpc_code"] == "G06F16/245"


def test_get_patent_by_application_number(peek_db: Path):
    conn = connect_readonly(peek_db)
    try:
        record = get_patent(conn, "US20200001111A1")
    finally:
        conn.close()

    assert record is not None
    assert record["document_type"] == "application"


def test_get_patent_missing(peek_db: Path):
    conn = connect_readonly(peek_db)
    try:
        assert get_patent(conn, "DOES-NOT-EXIST") is None
    finally:
        conn.close()


def test_cli_stats_json(peek_db: Path, capsys: pytest.CaptureFixture[str]):
    code = main(["--db", str(peek_db), "--json", "stats"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["patent_rows"] == 3


def test_cli_missing_db(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    missing = tmp_path / "absent.db"
    code = main(["--db", str(missing), "stats"])
    assert code == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()
