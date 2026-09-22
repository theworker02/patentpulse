"""Local SQLite / JSONL inspection CLI for PatentPulse corpora.

Inspect a processed ``patents.db`` without loading the full Hugging Face snapshot:

    python -m patentpulse.peek stats
    python -m patentpulse.peek search "sensor fusion" --limit 10
    python -m patentpulse.peek get 10000000
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from patentpulse.ingest import DEFAULT_DB_PATH, DEFAULT_JSONL_PATH

MISSING_DB_HINT = (
    "Local SQLite corpus not found at {path}.\n"
    "Run ingestion first, for example:\n"
    "  python -m patentpulse.ingest sync --source both --format both\n"
    "  python -m patentpulse.parse --input <weekly.zip> --output data/processed/patents.db\n"
    "Or load the published snapshot without a local DB:\n"
    "  from datasets import load_dataset\n"
    "  ds = load_dataset('theworker02/patentpulse')"
)

# Columns returned by search / get (keeps terminal output readable).
PEEK_COLUMNS = (
    "id",
    "patent_grant_id",
    "application_number",
    "publication_date",
    "invention_title",
    "abstract_text",
    "document_type",
    "source_file",
    "kind_code",
    "country",
    "filing_date",
    "claim_count",
)


class PeekError(Exception):
    """User-facing inspection error (missing DB, bad id, etc.)."""


def default_db_path() -> Path:
    return Path(DEFAULT_DB_PATH)


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    """Open a patents database read-only, or raise PeekError if missing."""
    path = Path(db_path)
    if not path.exists():
        raise PeekError(MISSING_DB_HINT.format(path=path))
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str = "patents") -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _has_fts(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name IN ('patents_fts', 'patent_fts') LIMIT 1"
    ).fetchone()
    return row is not None


def collect_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return row counts, date range, and document-type breakdown."""
    total = int(conn.execute("SELECT COUNT(*) FROM patents").fetchone()[0])
    type_rows = conn.execute(
        "SELECT document_type, COUNT(*) AS n FROM patents "
        "GROUP BY document_type ORDER BY n DESC"
    ).fetchall()
    date_row = conn.execute(
        "SELECT MIN(publication_date), MAX(publication_date) FROM patents "
        "WHERE publication_date IS NOT NULL AND publication_date != ''"
    ).fetchone()
    cpc_count = 0
    try:
        cpc_count = int(conn.execute("SELECT COUNT(*) FROM patent_cpc").fetchone()[0])
    except sqlite3.Error:
        pass

    return {
        "patent_rows": total,
        "cpc_rows": cpc_count,
        "publication_date_min": date_row[0] if date_row else None,
        "publication_date_max": date_row[1] if date_row else None,
        "document_types": {str(row["document_type"]): int(row["n"]) for row in type_rows},
    }


def search_patents(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Keyword search over title and abstract (FTS if present, else LIKE)."""
    q = (query or "").strip()
    if not q:
        return []
    limit = max(1, int(limit))
    columns = _table_columns(conn)
    select_cols = [c for c in PEEK_COLUMNS if c in columns]
    if not select_cols:
        select_cols = ["patent_grant_id", "invention_title", "abstract_text"]
    col_sql = ", ".join(select_cols)

    if _has_fts(conn):
        fts_name = "patents_fts"
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('patents_fts', 'patent_fts')"
            )
        }
        if "patents_fts" not in names:
            fts_name = "patent_fts"
        # Match FTS rowid to patents.id when available.
        sql = (
            f"SELECT {col_sql} FROM patents AS p "
            f"JOIN {fts_name} AS f ON f.rowid = p.id "
            f"WHERE {fts_name} MATCH ? "
            f"ORDER BY p.publication_date DESC "
            f"LIMIT ?"
        )
        try:
            rows = conn.execute(sql, (q, limit)).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            # Fall through to LIKE if FTS schema differs.
            pass

    pattern = f"%{q}%"
    sql = (
        f"SELECT {col_sql} FROM patents "
        "WHERE invention_title LIKE ? COLLATE NOCASE "
        "   OR abstract_text LIKE ? COLLATE NOCASE "
        "ORDER BY publication_date DESC "
        "LIMIT ?"
    )
    rows = conn.execute(sql, (pattern, pattern, limit)).fetchall()
    return [dict(row) for row in rows]


def get_patent(
    conn: sqlite3.Connection,
    identifier: str,
) -> dict[str, Any] | None:
    """Fetch one record by patent_grant_id or application_number."""
    ident = (identifier or "").strip()
    if not ident:
        return None
    columns = _table_columns(conn)
    select_cols = [c for c in PEEK_COLUMNS if c in columns]
    # Include longer text fields for single-record get.
    for extra in ("claims_text", "description_text", "background", "summary"):
        if extra in columns and extra not in select_cols:
            select_cols.append(extra)
    if not select_cols:
        select_cols = ["*"]
        col_sql = "*"
    else:
        col_sql = ", ".join(select_cols)

    row = conn.execute(
        f"SELECT {col_sql} FROM patents "
        "WHERE patent_grant_id = ? OR application_number = ? "
        "ORDER BY id LIMIT 1",
        (ident, ident),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)

    patent_id = result.get("id")
    if patent_id is not None:
        try:
            cpc_rows = conn.execute(
                "SELECT cpc_code, is_primary, position FROM patent_cpc "
                "WHERE patent_id = ? ORDER BY position, id",
                (patent_id,),
            ).fetchall()
            result["cpc_codes"] = [
                {
                    "cpc_code": r["cpc_code"],
                    "is_primary": bool(r["is_primary"]),
                    "position": r["position"],
                }
                for r in cpc_rows
            ]
        except sqlite3.Error:
            pass
    return result


def _truncate(text: str | None, width: int = 100) -> str:
    if text is None:
        return ""
    s = " ".join(str(text).split())
    if len(s) <= width:
        return s
    return s[: width - 1] + "…"


def print_stats(stats: dict[str, Any], *, db_path: Path) -> None:
    print("PatentPulse local corpus")
    print("=" * 40)
    print(f"Database:        {db_path}")
    print(f"Patent rows:     {stats['patent_rows']}")
    print(f"CPC rows:        {stats['cpc_rows']}")
    amin = stats.get("publication_date_min") or "—"
    amax = stats.get("publication_date_max") or "—"
    print(f"Date range:      {amin} → {amax}")
    print("Document types:")
    types = stats.get("document_types") or {}
    if not types:
        print("  (none)")
    else:
        for dtype, count in types.items():
            print(f"  {dtype or '(null)'}: {count}")


def print_search_results(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No matches.")
        return
    print(f"{len(rows)} match(es):")
    for i, row in enumerate(rows, 1):
        gid = row.get("patent_grant_id") or row.get("application_number") or "?"
        title = _truncate(row.get("invention_title"), 80)
        dtype = row.get("document_type") or ""
        date = row.get("publication_date") or ""
        print(f"{i}. [{dtype}] {gid}  {date}")
        print(f"   {title}")
        abstract = _truncate(row.get("abstract_text"), 120)
        if abstract:
            print(f"   {abstract}")


def print_record(record: dict[str, Any] | None, *, identifier: str) -> None:
    if record is None:
        print(f"No record found for id={identifier!r}")
        return
    # Prefer JSON for get so buyers can pipe into jq / notebooks.
    print(json.dumps(record, ensure_ascii=False, indent=2, default=str))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m patentpulse.peek",
        description="Inspect a local PatentPulse SQLite corpus (stats / search / get).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=f"Path to patents.db (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        default=None,
        help=f"Optional JSONL path for existence hints (default: {DEFAULT_JSONL_PATH})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON for stats and search (get always prints JSON).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("stats", help="Row counts, date range, document-type breakdown.")

    search_parser = subparsers.add_parser(
        "search",
        help="Keyword search over invention_title and abstract_text.",
    )
    search_parser.add_argument("query", help="Keyword or phrase to match.")
    search_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum rows to return (default: 20).",
    )

    get_parser = subparsers.add_parser(
        "get",
        help="Fetch one record by patent_grant_id or application_number.",
    )
    get_parser.add_argument(
        "id",
        help="Grant id (e.g. 10000000) or application number.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    db_path = Path(args.db) if args.db is not None else default_db_path()

    try:
        conn = connect_readonly(db_path)
    except PeekError as exc:
        print(str(exc), file=sys.stderr)
        jsonl = Path(args.jsonl) if args.jsonl is not None else Path(DEFAULT_JSONL_PATH)
        if jsonl.exists():
            print(
                f"\nNote: JSONL exists at {jsonl} but peek reads SQLite. "
                "Re-run ingest with --format sqlite or both.",
                file=sys.stderr,
            )
        return 1

    try:
        if args.command == "stats":
            stats = collect_stats(conn)
            if args.json:
                payload = {"database": str(db_path), **stats}
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_stats(stats, db_path=db_path)
            return 0

        if args.command == "search":
            rows = search_patents(conn, args.query, limit=args.limit)
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
            else:
                print_search_results(rows)
            return 0

        if args.command == "get":
            record = get_patent(conn, args.id)
            print_record(record, identifier=args.id)
            return 0 if record is not None else 2

        parser.error(f"Unknown command: {args.command}")
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
