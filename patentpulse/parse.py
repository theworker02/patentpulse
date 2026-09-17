#!/usr/bin/env python3
"""
High-throughput streaming parser for USPTO bulk patent grant/application XML.

Usage
-----
    python -m patentpulse.parse \\
        --input /path/to/ipg190423.xml \\
        --output /path/to/patents.db \\
        --format sqlite

    python -m patentpulse.parse \\
        --input /path/to/ipg190423.zip \\
        --output /path/to/patents.jsonl \\
        --format jsonl \\
        --limit 1000

Design
------
USPTO weekly bulk files concatenate thousands of standalone XML documents.
This module:

1. Streams the file and yields one complete document at a time (constant memory
   with respect to file size).
2. Parses each document with ``lxml.etree.iterparse``, clearing element subtrees
   after extraction.
3. Cleans abstract, description, and claims text for ML / retrieval workloads.
4. Persists normalized records to SQLite (relational) or JSON Lines (flat).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from patentpulse.extract import extract_patent_from_xml
from patentpulse.schema import JsonlPatentWriter, SQLitePatentWriter
from patentpulse.stream import iter_concatenated_documents, open_bulk_text

LOGGER = logging.getLogger("patentpulse")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_bulk_file(
    input_path: Path,
    output_path: Path,
    *,
    output_format: str = "sqlite",
    batch_size: int = 500,
    limit: int | None = None,
    skip_errors: bool = True,
) -> dict[str, int]:
    """
    Parse a USPTO bulk XML (or ZIP-wrapped XML) file into SQLite and/or JSONL.

    Returns ingestion statistics.
    """
    stats = {
        "documents_seen": 0,
        "documents_parsed": 0,
        "documents_failed": 0,
        "records_written": 0,
        "records_skipped": 0,
    }

    sqlite_writer: SQLitePatentWriter | None = None
    jsonl_writer: JsonlPatentWriter | None = None

    if output_format in {"sqlite", "both"}:
        sqlite_writer = SQLitePatentWriter(output_path.with_suffix(".db"), batch_size=batch_size)
    if output_format in {"jsonl", "both"}:
        jsonl_path = output_path if output_path.suffix == ".jsonl" else output_path.with_suffix(".jsonl")
        jsonl_writer = JsonlPatentWriter(jsonl_path)

    text_stream, zip_handle = open_bulk_text(input_path)
    start = time.perf_counter()

    try:
        for document_xml in iter_concatenated_documents(text_stream):
            stats["documents_seen"] += 1
            if limit is not None and stats["documents_parsed"] >= limit:
                break

            try:
                record = extract_patent_from_xml(
                    document_xml,
                    source_file=str(input_path),
                    use_iterparse=True,
                )
                if record.document_type == "unknown":
                    stats["documents_failed"] += 1
                    continue
            except Exception as exc:  # noqa: BLE001 — bulk ingestion must continue
                stats["documents_failed"] += 1
                if skip_errors:
                    LOGGER.warning(
                        "Document %s failed: %s",
                        stats["documents_seen"],
                        exc,
                    )
                    continue
                raise

            stats["documents_parsed"] += 1

            if sqlite_writer is not None:
                inserted_records = sqlite_writer.write(record)
                if jsonl_writer is not None:
                    for inserted_record in inserted_records:
                        jsonl_writer.write(inserted_record)
            elif jsonl_writer is not None:
                jsonl_writer.write(record)

            if stats["documents_parsed"] % 250 == 0:
                elapsed = time.perf_counter() - start
                rate = stats["documents_parsed"] / elapsed if elapsed else 0.0
                LOGGER.info(
                    "Parsed %s documents (%.1f docs/sec, %s failures)",
                    stats["documents_parsed"],
                    rate,
                    stats["documents_failed"],
                )
    finally:
        text_stream.close()
        if zip_handle is not None:
            zip_handle.close()
        if sqlite_writer is not None:
            inserted_records = sqlite_writer.close()
            if jsonl_writer is not None:
                for inserted_record in inserted_records:
                    jsonl_writer.write(inserted_record)
            stats["records_written"] = sqlite_writer.records_written
            stats["records_skipped"] = sqlite_writer.records_skipped
        if jsonl_writer is not None:
            jsonl_writer.close()
            if output_format == "jsonl":
                stats["records_written"] = jsonl_writer.records_written

    elapsed = time.perf_counter() - start
    LOGGER.info(
        "Finished in %.1fs — seen=%s parsed=%s failed=%s written=%s skipped=%s",
        elapsed,
        stats["documents_seen"],
        stats["documents_parsed"],
        stats["documents_failed"],
        stats["records_written"],
        stats["records_skipped"],
    )
    return stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stream-parse USPTO bulk patent XML into SQLite or JSONL.",
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        help="Path to USPTO bulk .xml file or .zip archive containing XML.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        type=Path,
        help="Output path (.db for sqlite, .jsonl for jsonl, base path for both).",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("sqlite", "jsonl", "both"),
        default="sqlite",
        help="Output format (default: sqlite).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="SQLite insert batch size (default: 500).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N successfully parsed documents (debug / sampling).",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort on the first document parse error.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    if not args.input.exists():
        LOGGER.error("Input file not found: %s", args.input)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        parse_bulk_file(
            args.input,
            args.output,
            output_format=args.format,
            batch_size=args.batch_size,
            limit=args.limit,
            skip_errors=not args.fail_fast,
        )
    except KeyboardInterrupt:
        LOGGER.warning("Interrupted by user.")
        return 130
    except Exception:
        LOGGER.exception("Fatal error during parsing.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
