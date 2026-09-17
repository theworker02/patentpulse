"""SQLite schema and batched persistence for extracted patent records."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import sqlite3
from pathlib import Path

from patentpulse.extract import PatentRecord

PATENTS_DDL = """
CREATE TABLE IF NOT EXISTS patents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patent_grant_id TEXT,
    application_number TEXT,
    publication_date TEXT,
    invention_title TEXT,
    abstract_text TEXT,
    description_text TEXT,
    claims_text TEXT,
    document_type TEXT NOT NULL,
    source_file TEXT,
    record_key TEXT,
    extracted_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (patent_grant_id, application_number, publication_date)
);

CREATE TABLE IF NOT EXISTS patent_cpc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patent_id INTEGER NOT NULL,
    cpc_code TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 1,
    position INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE,
    UNIQUE (patent_id, cpc_code)
);

CREATE INDEX IF NOT EXISTS idx_patents_grant_id ON patents(patent_grant_id);
CREATE INDEX IF NOT EXISTS idx_patents_application_number ON patents(application_number);
CREATE INDEX IF NOT EXISTS idx_patents_publication_date ON patents(publication_date);
CREATE INDEX IF NOT EXISTS idx_patent_cpc_code ON patent_cpc(cpc_code);
"""

EXTRA_PATENT_COLUMNS = (
    ("kind_code", "TEXT"),
    ("country", "TEXT"),
    ("language", "TEXT"),
    ("filing_date", "TEXT"),
    ("date_produced", "TEXT"),
    ("application_type", "TEXT"),
    ("claim_count", "INTEGER"),
    ("background", "TEXT"),
    ("summary", "TEXT"),
    ("examiner_name_last", "TEXT"),
    ("examiner_name_first", "TEXT"),
    ("inventors_json", "TEXT"),
    ("assignees_json", "TEXT"),
    ("ipc_codes_json", "TEXT"),
    ("citations_json", "TEXT"),
    ("npl_citations_json", "TEXT"),
    ("related_application_numbers_json", "TEXT"),
    ("record_key", "TEXT"),
)


def _record_key(record: PatentRecord) -> str:
    """Return a stable identity for deduplication across interrupted runs."""
    identifiers = (
        record.patent_grant_id or "",
        record.application_number or "",
        record.publication_date or "",
    )
    if any(identifiers):
        identity = "\x1f".join((record.document_type or "", *identifiers))
    else:
        identity = "\x1f".join(
            (record.document_type or "", record.invention_title or "", record.source_file or "")
        )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _ensure_columns(conn: sqlite3.Connection) -> bool:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(patents)")}
    was_empty = conn.execute("SELECT 1 FROM patents LIMIT 1").fetchone() is None
    for name, typedef in EXTRA_PATENT_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE patents ADD COLUMN {name} {typedef}")
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(patents)")}
    if "idx_patents_record_key" not in indexes and was_empty:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_patents_record_key "
            "ON patents(record_key)"
        )
        indexes.add("idx_patents_record_key")
    return "idx_patents_record_key" in indexes


class SQLitePatentWriter:
    """Batch writer with WAL mode and stable cross-run deduplication."""

    def __init__(self, db_path: Path, *, batch_size: int = 500) -> None:
        self.db_path = db_path
        self.batch_size = batch_size
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA temp_store=MEMORY;")
        self._conn.executescript(PATENTS_DDL)
        self._has_record_key_index = _ensure_columns(self._conn)
        self._pending: list[PatentRecord] = []
        self.records_written = 0
        self.records_skipped = 0

    def write(self, record: PatentRecord) -> list[PatentRecord]:
        self._pending.append(record)
        if len(self._pending) >= self.batch_size:
            return self.flush()
        return []

    def flush(self) -> list[PatentRecord]:
        if not self._pending:
            return []

        pending = self._pending
        self._pending = []
        inserted_records: list[PatentRecord] = []
        cpc_rows: list[tuple[int, str, int, int]] = []
        seen_keys: set[str] = set()

        with self._conn:
            for record in pending:
                key = _record_key(record)
                if key in seen_keys:
                    self.records_skipped += 1
                    continue
                seen_keys.add(key)

                row = None
                if self._has_record_key_index:
                    row = self._conn.execute(
                        "SELECT id FROM patents WHERE record_key = ? LIMIT 1",
                        (key,),
                    ).fetchone()
                patent_id = int(row["id"]) if row else self._lookup_patent_id(record)
                inserted = False

                if patent_id is None:
                    cursor = self._conn.execute(
                        """
                        INSERT OR IGNORE INTO patents (
                            patent_grant_id,
                            application_number,
                            publication_date,
                            invention_title,
                            abstract_text,
                            description_text,
                            claims_text,
                            document_type,
                            source_file,
                            record_key,
                            kind_code,
                            country,
                            language,
                            filing_date,
                            date_produced,
                            application_type,
                            claim_count,
                            background,
                            summary,
                            examiner_name_last,
                            examiner_name_first,
                            inventors_json,
                            assignees_json,
                            ipc_codes_json,
                            citations_json,
                            npl_citations_json,
                            related_application_numbers_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.patent_grant_id,
                            record.application_number,
                            record.publication_date,
                            record.invention_title,
                            record.abstract_text,
                            record.description_text,
                            record.claims_text,
                            record.document_type,
                            record.source_file,
                            key,
                            record.kind_code,
                            record.country,
                            record.language,
                            record.filing_date,
                            record.date_produced,
                            record.application_type,
                            record.claim_count,
                            record.background,
                            record.summary,
                            record.examiner_name_last,
                            record.examiner_name_first,
                            json.dumps([asdict(item) for item in record.inventor_list], ensure_ascii=False),
                            json.dumps(record.assignee_names, ensure_ascii=False),
                            json.dumps(record.ipc_codes, ensure_ascii=False),
                            json.dumps(record.cited_patent_ids, ensure_ascii=False),
                            json.dumps(record.npl_citations, ensure_ascii=False),
                            json.dumps(record.related_application_numbers, ensure_ascii=False),
                        ),
                    )
                    if cursor.rowcount == 1:
                        patent_id = int(cursor.lastrowid)
                        inserted = True
                    else:
                        row = None
                        if self._has_record_key_index:
                            row = self._conn.execute(
                                "SELECT id FROM patents WHERE record_key = ? LIMIT 1",
                                (key,),
                            ).fetchone()
                        patent_id = int(row["id"]) if row else self._lookup_patent_id(record)

                if inserted:
                    self.records_written += 1
                    inserted_records.append(record)
                else:
                    self.records_skipped += 1

                if patent_id is None:
                    continue
                codes = (
                    [(code, 1) for code in record.primary_cpc_codes]
                    + [(code, 0) for code in record.further_cpc_codes]
                )
                for position, (code, is_primary) in enumerate(codes):
                    cpc_rows.append((patent_id, code, is_primary, position))

            if cpc_rows:
                self._conn.executemany(
                    """
                    INSERT OR IGNORE INTO patent_cpc (
                        patent_id, cpc_code, is_primary, position
                    ) VALUES (?, ?, ?, ?)
                    """,
                    cpc_rows,
                )

        return inserted_records

    def _lookup_patent_id(self, record: PatentRecord) -> int | None:
        row = self._conn.execute(
            """
            SELECT id FROM patents
            WHERE patent_grant_id IS ?
              AND application_number IS ?
              AND publication_date IS ?
            LIMIT 1
            """,
            (record.patent_grant_id, record.application_number, record.publication_date),
        ).fetchone()
        return int(row["id"]) if row else None

    def close(self) -> list[PatentRecord]:
        inserted_records = self.flush()
        self._conn.close()
        return inserted_records


class JsonlPatentWriter:
    """Append-only JSON Lines writer with per-run duplicate suppression."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = path.open("a", encoding="utf-8", newline="\n")
        self._seen_keys: set[str] = set()
        self.records_written = 0

    def write(self, record: PatentRecord) -> bool:
        key = _record_key(record)
        if key in self._seen_keys:
            return False
        self._seen_keys.add(key)
        self._handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        self.records_written += 1
        return True

    def flush(self) -> None:
        self._handle.flush()

    def close(self) -> None:
        self.flush()
        self._handle.close()
