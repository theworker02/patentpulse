"""Hard quality, throughput, corpus-size, and error-rate measurements.

The published Hugging Face snapshot is the authority for corpus-scale counts.
This module re-reads that snapshot's ``release_manifest.json`` and Parquet
footers (HTTP range requests, no full download) and runs a local, deterministic
ingestion benchmark against an expanded copy of the in-repo fixture.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import platform
import re
import resource
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from patentpulse.extract import PatentRecord, extract_patent_from_xml
from patentpulse.parse import parse_bulk_file
from patentpulse.schema import _record_key
from patentpulse.stream import iter_concatenated_documents

HUB_DATASET = "theworker02/patentpulse"
HUB_TREE_URL = (
    "https://huggingface.co/api/datasets/theworker02/patentpulse/tree/main?recursive=1"
)
HUB_RESOLVE_URL = "https://huggingface.co/datasets/theworker02/patentpulse/resolve/main/{path}"
HUB_USER_AGENT = "PatentPulse-metrics/1.0 (+https://github.com/theworker02/patentpulse)"
CORE_SCALAR_FIELDS = (
    "patent_grant_id",
    "application_number",
    "publication_date",
    "invention_title",
    "abstract_text",
    "description_text",
    "claims_text",
    "document_type",
    "source_file",
    "main_cpc_label",
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEQUENCE_LISTING_STUB = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE sequence-cwu SYSTEM "us-sequence-listing-v1_3-2020-10-08.dtd" [ ]>
<sequence-cwu lang="EN">
  <s100>PatentPulse unknown-root fixture</s100>
</sequence-cwu>
"""
TRUNCATED_XML_STUB = """<?xml version="1.0" encoding="UTF-8"?>
<us-patent-grant lang="EN">
  <us-bibliographic-data-grant>
    <invention-title>Broken
"""


class MetricsError(RuntimeError):
    """A measurement could not be completed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def human_bytes(n: int | float) -> str:
    value = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024.0 or unit == "TiB":
            return f"{value:,.2f} {unit}"
        value /= 1024.0
    return f"{n} B"


def human_decimal_bytes(n: int | float) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1000.0 or unit == "TB":
            return f"{value:,.2f} {unit}"
        value /= 1000.0
    return f"{n} B"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def fixture_path() -> Path:
    return repo_root() / "tests" / "fixtures" / "sample_bulk.xml"


def host_environment() -> dict[str, Any]:
    uname = platform.uname()
    return {
        "collected_at": utc_now(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": uname.machine,
        "processor": uname.processor or platform.processor(),
        "cpu_count": os.cpu_count(),
        "cpu_model": _cpu_model(),
        "memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        if hasattr(os, "sysconf")
        else None,
    }


def _cpu_model() -> str | None:
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.exists():
        return platform.processor() or None
    for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return None


def rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # Linux reports ru_maxrss in kilobytes.
    return int(usage.ru_maxrss) * 1024


def _http_get(url: str, *, extra_headers: Mapping[str, str] | None = None, timeout: int = 120) -> tuple[bytes, dict[str, str]]:
    headers = {"User-Agent": HUB_USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return body, {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.URLError as exc:
        raise MetricsError(f"HTTP GET failed for {url}: {exc}") from exc


def fetch_json(url: str) -> Any:
    body, _headers = _http_get(url)
    return json.loads(body.decode("utf-8"))


def fetch_hub_tree() -> list[dict[str, Any]]:
    payload = fetch_json(HUB_TREE_URL)
    if not isinstance(payload, list):
        raise MetricsError("Unexpected Hugging Face tree payload.")
    return payload


def fetch_release_manifest() -> dict[str, Any]:
    url = HUB_RESOLVE_URL.format(path="release_manifest.json")
    payload = fetch_json(url)
    if not isinstance(payload, dict):
        raise MetricsError("release_manifest.json is not an object.")
    return payload


class _TailFile(io.RawIOBase):
    """Random-access file-like object backed by the last N bytes of a remote file."""

    def __init__(self, size: int, tail: bytes) -> None:
        super().__init__()
        self._size = size
        self._tail_start = size - len(tail)
        self._tail = tail
        self._pos = 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = self._size + offset
        else:
            raise ValueError(f"invalid whence: {whence}")
        if self._pos < 0:
            self._pos = 0
        return self._pos

    def tell(self) -> int:
        return self._pos

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self._size - self._pos
        if n == 0 or self._pos >= self._size:
            return b""
        if self._pos < self._tail_start:
            raise OSError(
                f"Parquet metadata read landed at byte {self._pos}, "
                f"before cached tail start {self._tail_start}."
            )
        start = self._pos - self._tail_start
        data = self._tail[start : start + n]
        self._pos += len(data)
        return bytes(data)

    def readinto(self, buffer) -> int:  # type: ignore[no-untyped-def]
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


def _read_remote_parquet_metadata(path: str, size: int) -> dict[str, Any]:
    import pyarrow.parquet as pq

    url = HUB_RESOLVE_URL.format(path=path)
    tail_bytes, headers = _http_get(url, extra_headers={"Range": "bytes=-8"})
    content_range = headers.get("content-range", "")
    if "/" in content_range:
        size = int(content_range.rsplit("/", 1)[-1])
    if len(tail_bytes) < 8 or tail_bytes[-4:] != b"PAR1":
        raise MetricsError(f"{path} is not a Parquet file.")
    footer_length = int.from_bytes(tail_bytes[:4], "little")
    # Footer + 4-byte length + 4-byte magic, with headroom for the PAR1 prefix.
    fetch = footer_length + 8
    tail, _headers = _http_get(url, extra_headers={"Range": f"bytes=-{fetch}"})
    handle = io.BufferedReader(_TailFile(size, tail), buffer_size=len(tail))
    metadata = pq.read_metadata(handle)

    compressed = 0
    uncompressed = 0
    nulls: dict[str, dict[str, int]] = {}
    column_bytes: dict[str, dict[str, int]] = {}
    for group_index in range(metadata.num_row_groups):
        group = metadata.row_group(group_index)
        for column_index in range(group.num_columns):
            column = group.column(column_index)
            name = column.path_in_schema
            compressed += column.total_compressed_size
            uncompressed += column.total_uncompressed_size
            bucket = column_bytes.setdefault(name, {"compressed": 0, "uncompressed": 0})
            bucket["compressed"] += column.total_compressed_size
            bucket["uncompressed"] += column.total_uncompressed_size
            stats = column.statistics
            observed = nulls.setdefault(name, {"nulls": 0, "rows": 0, "has_stats": 0})
            observed["rows"] += group.num_rows
            if stats is not None and stats.null_count is not None:
                observed["nulls"] += int(stats.null_count)
                observed["has_stats"] += group.num_rows

    return {
        "path": path,
        "file_bytes": size,
        "num_rows": metadata.num_rows,
        "num_row_groups": metadata.num_row_groups,
        "num_columns": metadata.num_columns,
        "serialized_footer_bytes": metadata.serialized_size,
        "created_by": metadata.created_by,
        "column_chunk_compressed_bytes": compressed,
        "column_chunk_uncompressed_bytes": uncompressed,
        "column_bytes": column_bytes,
        "nulls": nulls,
    }


def inventory_published_parquet(
    tree: list[dict[str, Any]] | None = None,
    *,
    workers: int = 8,
) -> dict[str, Any]:
    """Read every published Parquet footer's row counts, nulls, and sizes."""
    tree = tree if tree is not None else fetch_hub_tree()
    files = [
        item
        for item in tree
        if item.get("type") == "file" and str(item.get("path", "")).endswith(".parquet")
    ]
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    def _one(item: dict[str, Any]) -> dict[str, Any]:
        path = str(item["path"])
        return _read_remote_parquet_metadata(path, int(item.get("size") or 0))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, item): item for item in files}
        for future in as_completed(futures):
            item = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 — inventory must continue
                errors.append({"path": str(item.get("path")), "error": str(exc)})

    results.sort(key=lambda row: row["path"])
    by_split: dict[str, dict[str, int]] = defaultdict(lambda: {
        "shards": 0,
        "rows": 0,
        "file_bytes": 0,
        "column_chunk_compressed_bytes": 0,
        "column_chunk_uncompressed_bytes": 0,
    })
    nulls: dict[str, dict[str, int]] = {}
    column_bytes: dict[str, dict[str, int]] = {}
    for shard in results:
        split = shard["path"].split("/")[1]
        bucket = by_split[split]
        bucket["shards"] += 1
        bucket["rows"] += shard["num_rows"]
        bucket["file_bytes"] += shard["file_bytes"]
        bucket["column_chunk_compressed_bytes"] += shard["column_chunk_compressed_bytes"]
        bucket["column_chunk_uncompressed_bytes"] += shard["column_chunk_uncompressed_bytes"]
        for name, values in shard["nulls"].items():
            observed = nulls.setdefault(name, {"nulls": 0, "rows": 0, "has_stats": 0})
            for key, value in values.items():
                observed[key] += value
        for name, values in shard["column_bytes"].items():
            observed_bytes = column_bytes.setdefault(name, {"compressed": 0, "uncompressed": 0})
            observed_bytes["compressed"] += values["compressed"]
            observed_bytes["uncompressed"] += values["uncompressed"]

    fill_rates = {}
    for name, values in nulls.items():
        rows = values["has_stats"] or values["rows"]
        fill_rates[name] = {
            "rows_with_statistics": values["has_stats"],
            "nulls": values["nulls"],
            "fill_rate": (1.0 - (values["nulls"] / rows)) if rows else None,
        }

    total_file = sum(shard["file_bytes"] for shard in results)
    total_comp = sum(shard["column_chunk_compressed_bytes"] for shard in results)
    total_uncomp = sum(shard["column_chunk_uncompressed_bytes"] for shard in results)
    total_rows = sum(shard["num_rows"] for shard in results)
    return {
        "dataset": HUB_DATASET,
        "collected_at": utc_now(),
        "shard_count": len(results),
        "shard_errors": errors,
        "rows": total_rows,
        "file_bytes": total_file,
        "column_chunk_compressed_bytes": total_comp,
        "column_chunk_uncompressed_bytes": total_uncomp,
        "parquet_page_compression_ratio": (total_comp / total_uncomp) if total_uncomp else None,
        "bytes_per_row_compressed": (total_file / total_rows) if total_rows else None,
        "bytes_per_row_uncompressed_pages": (total_uncomp / total_rows) if total_rows else None,
        "by_split": dict(by_split),
        "fill_rates": fill_rates,
        "column_bytes": column_bytes,
        "shards": results,
    }


def summarize_release_errors(manifest: Mapping[str, Any]) -> dict[str, Any]:
    seen = int(manifest["records_seen"])
    written = int(manifest["records_written"])
    duplicates = int(manifest["duplicates_skipped"])
    invalid_rows = list(manifest.get("invalid_json_rows") or [])
    invalid = len(invalid_rows)
    jsonl_attempts = seen + invalid
    reasons = Counter(str(row.get("error", "unknown")) for row in invalid_rows)
    return {
        "source_file": manifest.get("source_file"),
        "source_bytes": int(manifest["source_bytes"]),
        "created_at": manifest.get("created_at"),
        "canonical_sha256": manifest.get("canonical_sha256"),
        "records_seen": seen,
        "records_written": written,
        "duplicates_skipped": duplicates,
        "invalid_json_rows": invalid,
        "jsonl_rows_attempted": jsonl_attempts,
        "duplicate_rate_of_valid_json": duplicates / seen if seen else None,
        "unique_yield_of_valid_json": written / seen if seen else None,
        "invalid_json_rate_of_attempted_rows": invalid / jsonl_attempts if jsonl_attempts else None,
        "identity_check_seen_minus_duplicates_equals_written": seen - duplicates == written,
        "invalid_json_by_reason": dict(reasons),
        "records_by_split": dict(manifest.get("records_by_split") or {}),
        "shards_by_split": dict(manifest.get("shards_by_split") or {}),
    }


def corpus_inventory(
    *,
    manifest: Mapping[str, Any],
    tree: list[dict[str, Any]],
    parquet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compressed and uncompressed sizes for the published snapshot."""
    parquet_files = [
        item
        for item in tree
        if item.get("type") == "file" and str(item.get("path", "")).endswith(".parquet")
    ]
    sidecar_files = [
        item
        for item in tree
        if item.get("type") == "file" and not str(item.get("path", "")).endswith(".parquet")
    ]
    parquet_bytes = sum(int(item.get("size") or 0) for item in parquet_files)
    sidecar_bytes = sum(int(item.get("size") or 0) for item in sidecar_files)
    jsonl_bytes = int(manifest["source_bytes"])
    written = int(manifest["records_written"])
    page_uncompressed = int(parquet["column_chunk_uncompressed_bytes"]) if parquet else None
    page_compressed = int(parquet["column_chunk_compressed_bytes"]) if parquet else None
    return {
        "collected_at": utc_now(),
        "dataset": HUB_DATASET,
        "jsonl_input_bytes": jsonl_bytes,
        "jsonl_input_gib": jsonl_bytes / 1024**3,
        "jsonl_input_gb": jsonl_bytes / 1000**3,
        "published_parquet_file_bytes": parquet_bytes,
        "published_parquet_gib": parquet_bytes / 1024**3,
        "published_parquet_gb": parquet_bytes / 1000**3,
        "published_sidecar_bytes": sidecar_bytes,
        "hub_repo_file_bytes": parquet_bytes + sidecar_bytes,
        "jsonl_to_parquet_file_ratio": parquet_bytes / jsonl_bytes if jsonl_bytes else None,
        "parquet_page_uncompressed_bytes": page_uncompressed,
        "parquet_page_compressed_bytes": page_compressed,
        "parquet_page_compression_ratio": (
            page_compressed / page_uncompressed if page_uncompressed else None
        ),
        "jsonl_bytes_per_unique_record": jsonl_bytes / written if written else None,
        "parquet_file_bytes_per_unique_record": parquet_bytes / written if written else None,
        "raw_uspto_archives_claim": {
            "statement": "Project documentation describes official weekly USPTO ZIP archives on the order of 1.6 TB before deletion.",
            "measured_here": False,
            "reason": "Completed archives are deleted after ingest; bulkdata.uspto.gov is not required to size the published snapshot.",
        },
        "notes": [
            "JSONL input is the uncompressed append-only ingestion artifact that produced this snapshot.",
            "Parquet files are Zstandard-compressed shards with dictionary encoding.",
            "Parquet page uncompressed bytes are the decoded Arrow/Parquet column pages, not the JSONL source.",
        ],
    }


def uniquify_document(document: str, index: int) -> str:
    grant_id = f"{10_000_000 + index:08d}"
    application_number = f"{15_000_000 + index:08d}"
    seen = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal seen
        seen += 1
        if seen == 1:
            return f"<doc-number>{grant_id}</doc-number>"
        if seen == 2:
            return f"<doc-number>{application_number}</doc-number>"
        return match.group(0)

    return re.sub(r"<doc-number>\d+</doc-number>", replace, document)


def materialize_benchmark_xml(
    destination: Path,
    *,
    documents: int,
    fixture: Path | None = None,
    unknown_documents: int = 0,
    truncated_documents: int = 0,
    duplicate_fraction: float = 0.0,
) -> dict[str, int]:
    """Write a concatenated USPTO-like bulk file with unique (or mixed) IDs."""
    fixture = fixture or fixture_path()
    templates = list(iter_concatenated_documents(fixture.open("r", encoding="utf-8")))
    if not templates:
        raise MetricsError(f"Fixture contained no documents: {fixture}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    unique_documents = 0
    duplicate_documents = 0
    duplicate_count = int(round(documents * duplicate_fraction)) if duplicate_fraction else 0
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(documents):
            source = templates[index % len(templates)]
            identity = index
            if duplicate_count and index >= documents - duplicate_count:
                identity = index - (documents - duplicate_count)
                duplicate_documents += 1
            else:
                unique_documents += 1
            source = uniquify_document(source, identity)
            handle.write(source)
            if not source.endswith("\n"):
                handle.write("\n")
        for _ in range(unknown_documents):
            handle.write(SEQUENCE_LISTING_STUB)
            if not SEQUENCE_LISTING_STUB.endswith("\n"):
                handle.write("\n")
        for _ in range(truncated_documents):
            handle.write(TRUNCATED_XML_STUB)
            if not TRUNCATED_XML_STUB.endswith("\n"):
                handle.write("\n")
    return {
        "patent_documents": documents,
        "unique_identities": unique_documents,
        "duplicate_identities": duplicate_documents,
        "unknown_documents": unknown_documents,
        "truncated_documents": truncated_documents,
        "bytes": destination.stat().st_size,
    }


def _length_stats(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "max": None, "mean": None, "p50": None, "p95": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return {
        "n": len(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
        "p50": statistics.median(ordered),
        "p95": ordered[p95_index],
    }


def quality_from_records(records: Iterable[PatentRecord]) -> dict[str, Any]:
    rows = list(records)
    present = Counter()
    aliases_ok = 0
    dates_ok = 0
    boilerplate_leaks = 0
    empty_core = 0
    keys = [_record_key(record) for record in rows]
    for record in rows:
        payload = record.to_dict()
        for field in CORE_SCALAR_FIELDS:
            value = payload.get(field)
            if value not in (None, "", []):
                present[field] += 1
        if (
            payload.get("title") == payload.get("invention_title")
            and payload.get("abstract") == payload.get("abstract_text")
            and payload.get("claims") == payload.get("claims_text")
            and payload.get("full_description") == payload.get("description_text")
        ):
            aliases_ok += 1
        pub = payload.get("publication_date")
        if isinstance(pub, str) and DATE_RE.match(pub):
            dates_ok += 1
        description = payload.get("description_text") or ""
        if "CROSS-REFERENCE" in description:
            boilerplate_leaks += 1
        if not payload.get("abstract_text") or not payload.get("claims_text") or not payload.get("invention_title"):
            empty_core += 1

    n = len(rows)
    return {
        "records": n,
        "unique_record_keys": len(set(keys)),
        "duplicate_record_keys": n - len(set(keys)),
        "fill_rates": {field: (present[field] / n if n else None) for field in CORE_SCALAR_FIELDS},
        "alias_consistency_rate": aliases_ok / n if n else None,
        "iso_publication_date_rate": dates_ok / n if n else None,
        "boilerplate_leak_rate": boilerplate_leaks / n if n else None,
        "missing_title_abstract_or_claims_rate": empty_core / n if n else None,
        "document_types": dict(Counter(record.document_type for record in rows)),
        "text_chars": {
            "abstract_text": _length_stats([len(record.abstract_text or "") for record in rows]),
            "claims_text": _length_stats([len(record.claims_text or "") for record in rows]),
            "description_text": _length_stats([len(record.description_text or "") for record in rows]),
        },
        "cpc_labels_per_record": _length_stats(
            [len(record.primary_cpc_codes) + len(record.further_cpc_codes) for record in rows]
        ),
    }


def extract_records_from_bulk(path: Path, *, limit: int | None = None) -> list[PatentRecord]:
    records: list[PatentRecord] = []
    text_stream, zip_handle = None, None
    from patentpulse.stream import open_bulk_text

    text_stream, zip_handle = open_bulk_text(path)
    try:
        for document in iter_concatenated_documents(text_stream):
            record = extract_patent_from_xml(document, source_file=str(path), use_iterparse=True)
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    finally:
        if text_stream is not None:
            text_stream.close()
        if zip_handle is not None:
            zip_handle.close()
    return records


def benchmark_ingestion(
    *,
    documents: int = 2_000,
    work_dir: Path | None = None,
    unknown_documents: int = 25,
    truncated_documents: int = 5,
    duplicate_fraction: float = 0.08,
) -> dict[str, Any]:
    """Measure parse/write throughput and local dedup/error rates."""
    work_dir = work_dir or Path("data/metrics-work")
    work_dir.mkdir(parents=True, exist_ok=True)
    unique_xml = work_dir / "benchmark-unique.xml"
    mixed_xml = work_dir / "benchmark-mixed.xml"
    unique_meta = materialize_benchmark_xml(unique_xml, documents=documents)
    mixed_meta = materialize_benchmark_xml(
        mixed_xml,
        documents=documents,
        unknown_documents=unknown_documents,
        truncated_documents=truncated_documents,
        duplicate_fraction=duplicate_fraction,
    )

    unique_out = work_dir / "unique-patents"
    mixed_out = work_dir / "mixed-patents"
    for leftover in unique_out.with_suffix(".db"), unique_out.with_suffix(".jsonl"):
        leftover.unlink(missing_ok=True)
    for leftover in mixed_out.with_suffix(".db"), mixed_out.with_suffix(".jsonl"):
        leftover.unlink(missing_ok=True)

    start_rss = rss_bytes()
    started = time.perf_counter()
    unique_stats = parse_bulk_file(unique_xml, unique_out, output_format="both", batch_size=250)
    unique_seconds = time.perf_counter() - started
    unique_rss = rss_bytes()

    started = time.perf_counter()
    mixed_stats = parse_bulk_file(mixed_xml, mixed_out, output_format="both", batch_size=250)
    mixed_seconds = time.perf_counter() - started
    mixed_rss = rss_bytes()

    # Second pass on the unique file measures cross-run SQLite deduplication.
    started = time.perf_counter()
    replay_stats = parse_bulk_file(unique_xml, unique_out, output_format="sqlite", batch_size=250)
    replay_seconds = time.perf_counter() - started

    sample = extract_records_from_bulk(unique_xml, limit=min(documents, 400))
    quality = quality_from_records(record for record in sample if record.document_type != "unknown")

    unique_rate = unique_stats["documents_parsed"] / unique_seconds if unique_seconds else None
    return {
        "collected_at": utc_now(),
        "environment": host_environment(),
        "input": {
            "unique": unique_meta,
            "mixed": mixed_meta,
        },
        "unique_pass": {
            "seconds": unique_seconds,
            "docs_per_second": unique_rate,
            "records_per_second": unique_stats["records_written"] / unique_seconds if unique_seconds else None,
            "peak_rss_bytes": unique_rss,
            "rss_delta_bytes": unique_rss - start_rss,
            **unique_stats,
        },
        "mixed_pass": {
            "seconds": mixed_seconds,
            "docs_per_second": mixed_stats["documents_parsed"] / mixed_seconds if mixed_seconds else None,
            **mixed_stats,
            "configured_unknown_documents": unknown_documents,
            "configured_truncated_documents": truncated_documents,
            "configured_duplicate_fraction": duplicate_fraction,
            "parse_failure_rate": (
                mixed_stats["documents_failed"]
                / mixed_stats["documents_seen"]
                if mixed_stats["documents_seen"]
                else None
            ),
            "write_skip_rate": (
                mixed_stats["records_skipped"]
                / (mixed_stats["records_written"] + mixed_stats["records_skipped"])
                if (mixed_stats["records_written"] + mixed_stats["records_skipped"])
                else None
            ),
        },
        "replay_pass": {
            "seconds": replay_seconds,
            **replay_stats,
            "expected_all_skipped": replay_stats["records_written"] == 0,
        },
        "fixture_quality_sample": quality,
        "output_bytes": {
            "unique_sqlite": (unique_out.with_suffix(".db")).stat().st_size
            if unique_out.with_suffix(".db").exists()
            else 0,
            "unique_jsonl": (unique_out.with_suffix(".jsonl")).stat().st_size
            if unique_out.with_suffix(".jsonl").exists()
            else 0,
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_reports(
    output_dir: Path,
    *,
    documents: int = 2_000,
    skip_hub: bool = False,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """Collect every buyer-facing measurement and persist JSON artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    environment = host_environment()
    write_json(output_dir / "environment.json", environment)

    if skip_hub:
        manifest = json.loads((output_dir / "hf_release_manifest.json").read_text(encoding="utf-8"))
        tree: list[dict[str, Any]] = []
        parquet: dict[str, Any] | None = None
        errors = summarize_release_errors(manifest)
        sizes = corpus_inventory(manifest=manifest, tree=tree, parquet=parquet)
    else:
        manifest = fetch_release_manifest()
        tree = fetch_hub_tree()
        write_json(output_dir / "hf_release_manifest.json", manifest)
        write_json(output_dir / "hf_tree.json", tree)
        parquet = inventory_published_parquet(tree)
        write_json(output_dir / "parquet_inventory.json", parquet)
        errors = summarize_release_errors(manifest)
        sizes = corpus_inventory(manifest=manifest, tree=tree, parquet=parquet)

    write_json(output_dir / "dedup_and_errors.json", errors)
    write_json(output_dir / "corpus_inventory.json", sizes)

    benchmark = benchmark_ingestion(documents=documents, work_dir=work_dir or output_dir / "work")
    write_json(output_dir / "ingestion_benchmark.json", benchmark)

    quality = {
        "collected_at": utc_now(),
        "published_snapshot": {
            "fill_rates": (parquet or {}).get("fill_rates"),
            "rows_measured": (parquet or {}).get("rows"),
            "method": "Parquet footer statistics over every published shard (no row-group payload download).",
        },
        "local_fixture_sample": benchmark["fixture_quality_sample"],
        "dedup_and_errors": errors,
    }
    write_json(output_dir / "quality_report.json", quality)

    index = {
        "collected_at": utc_now(),
        "dataset": HUB_DATASET,
        "artifacts": sorted(path.name for path in output_dir.glob("*.json")),
        "headline": {
            "unique_records": errors["records_written"],
            "jsonl_input_bytes": sizes["jsonl_input_bytes"],
            "parquet_file_bytes": sizes.get("published_parquet_file_bytes"),
            "duplicate_rate": errors["duplicate_rate_of_valid_json"],
            "invalid_json_rows": errors["invalid_json_rows"],
            "ingest_docs_per_second": benchmark["unique_pass"]["docs_per_second"],
        },
    }
    write_json(output_dir / "index.json", index)
    return index


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure PatentPulse quality, size, and throughput.")
    parser.add_argument("--output", type=Path, default=Path("docs/acquisition/metrics"))
    parser.add_argument("--documents", type=int, default=2_000, help="Unique patent documents for the local ingest benchmark.")
    parser.add_argument("--skip-hub", action="store_true", help="Reuse a previously downloaded release_manifest.json.")
    parser.add_argument("--work-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        index = build_reports(
            args.output,
            documents=args.documents,
            skip_hub=args.skip_hub,
            work_dir=args.work_dir,
        )
    except (MetricsError, OSError, ValueError) as exc:
        print(f"Metrics failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
