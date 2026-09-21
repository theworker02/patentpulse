"""Create and validate a stable, Hugging Face-ready PatentPulse release."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from patentpulse.manifest import IngestManifest

DEFAULT_MAX_SHARD_BYTES = 5_000_000_000
DEFAULT_ROW_GROUP_BYTES = 64_000_000
# Keep a meaningful floor for any export, then scale from the projected output
# size. A fixed 64 GB minimum made small validation releases and their tests
# fail on otherwise suitable machines.
MIN_FREE_SPACE_BYTES = 2_000_000_000
OUTPUT_HEADROOM_MULTIPLIER = 1.2
DEFAULT_EXPECTED_COMPRESSION_RATIO = 0.25

TEXT_FIELDS = (
    "patent_grant_id", "application_number", "publication_date", "invention_title",
    "abstract_text", "description_text", "claims_text", "document_type", "source_file",
    "kind_code", "country", "language", "filing_date", "date_produced", "application_type",
    "background", "summary", "examiner_name_last", "examiner_name_first", "patent_number",
    "publication_number", "title", "abstract", "claims", "full_description", "date_published",
    "patent_issue_date", "main_cpc_label", "main_ipcr_label",
)
LIST_FIELDS = (
    "primary_cpc_codes", "further_cpc_codes", "ipc_codes", "assignee_names", "cited_patent_ids",
    "npl_citations", "related_application_numbers", "cpc_labels", "ipcr_labels", "cited_patents",
)
INVENTOR_FIELDS = (
    "inventor_name_last", "inventor_name_first", "inventor_city", "inventor_state", "inventor_country",
)
HF_FIELD_NAMES = (*TEXT_FIELDS, "claim_count", *LIST_FIELDS, "inventor_list")


class ReleaseError(RuntimeError):
    """Base exception for a release that cannot safely be produced."""


class ReleaseReadinessError(ReleaseError):
    """The source corpus is not stable enough to release."""


class ReleaseValidationError(ReleaseError):
    """A release does not meet its documented contract."""


@dataclass(frozen=True)
class ReleaseSummary:
    created_at: str
    source_file: str
    source_bytes: int
    records_seen: int
    records_written: int
    duplicates_skipped: int
    invalid_json_rows: list[dict[str, Any]]
    records_by_split: dict[str, int]
    shards_by_split: dict[str, int]
    canonical_sha256: str
    max_shard_bytes: int


def _require_pyarrow() -> tuple[Any, Any]:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise ReleaseError(
            "PyArrow is required. Install dependencies with `python -m pip install -r requirements.txt`."
        ) from exc
    return pa, pq


def hf_arrow_schema() -> Any:
    """The one Arrow schema used by every Parquet shard."""
    pa, _ = _require_pyarrow()
    inventor = pa.struct([(field, pa.string()) for field in INVENTOR_FIELDS])
    fields = [pa.field(name, pa.string()) for name in TEXT_FIELDS]
    fields.append(pa.field("claim_count", pa.int32()))
    fields.extend(pa.field(name, pa.list_(pa.string())) for name in LIST_FIELDS)
    fields.append(pa.field("inventor_list", pa.list_(inventor)))
    return pa.schema(fields)


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, (str, int, float, bool)):
        text = str(value).strip()
        return text or None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                return [stripped]
        else:
            return [stripped]
    if not isinstance(value, (list, tuple, set)):
        value = [value]
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _coerce_text(item)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _coerce_inventors(value: Any) -> list[dict[str, str | None]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = []
    if not isinstance(value, list):
        return []
    output: list[dict[str, str | None]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        inventor = {field: _coerce_text(item.get(field)) for field in INVENTOR_FIELDS}
        if any(inventor.values()):
            output.append(inventor)
    return output


def _first_text(record: Mapping[str, Any], *names: str) -> str | None:
    for name in names:
        value = _coerce_text(record.get(name))
        if value is not None:
            return value
    return None


def _safe_source_name(value: Any) -> str | None:
    source = _coerce_text(value)
    return source.replace("\\", "/").rsplit("/", 1)[-1] if source else None


def normalize_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize historical and current JSONL rows into one public contract."""
    primary_cpc_codes = _coerce_list(record.get("primary_cpc_codes"))
    cpc_labels = _coerce_list(record.get("cpc_labels"))
    main_cpc = _first_text(record, "main_cpc_label")
    if not primary_cpc_codes and main_cpc:
        primary_cpc_codes = [main_cpc]
    if not cpc_labels:
        cpc_labels = list(primary_cpc_codes)
    if not main_cpc and primary_cpc_codes:
        main_cpc = primary_cpc_codes[0]

    ipc_codes = _coerce_list(record.get("ipc_codes", record.get("ipcr_labels")))
    ipcr_labels = _coerce_list(record.get("ipcr_labels")) or list(ipc_codes)
    main_ipcr = _first_text(record, "main_ipcr_label") or (ipc_codes[0] if ipc_codes else None)
    patent_id = _first_text(record, "patent_grant_id", "patent_number", "publication_number")
    publication_date = _first_text(record, "publication_date", "date_published", "patent_issue_date")
    title = _first_text(record, "invention_title", "title")
    abstract = _first_text(record, "abstract_text", "abstract")
    claims = _first_text(record, "claims_text", "claims")
    description = _first_text(record, "description_text", "full_description")
    document_type = (_first_text(record, "document_type") or "unknown").lower()
    if document_type not in {"grant", "application", "unknown"}:
        document_type = "unknown"
    try:
        claim_count = int(record["claim_count"]) if record.get("claim_count") is not None else None
    except (TypeError, ValueError):
        claim_count = None

    normalized: dict[str, Any] = {
        "patent_grant_id": patent_id,
        "application_number": _first_text(record, "application_number"),
        "publication_date": publication_date,
        "invention_title": title,
        "abstract_text": abstract,
        "description_text": description,
        "claims_text": claims,
        "document_type": document_type,
        "source_file": _safe_source_name(record.get("source_file")),
        "kind_code": _first_text(record, "kind_code"),
        "country": _first_text(record, "country"),
        "language": _first_text(record, "language"),
        "filing_date": _first_text(record, "filing_date"),
        "date_produced": _first_text(record, "date_produced"),
        "application_type": _first_text(record, "application_type"),
        "background": _first_text(record, "background"),
        "summary": _first_text(record, "summary"),
        "examiner_name_last": _first_text(record, "examiner_name_last"),
        "examiner_name_first": _first_text(record, "examiner_name_first"),
        "patent_number": patent_id,
        "publication_number": patent_id,
        "title": title,
        "abstract": abstract,
        "claims": claims,
        "full_description": description,
        "date_published": publication_date,
        "patent_issue_date": publication_date if document_type == "grant" else None,
        "main_cpc_label": main_cpc,
        "main_ipcr_label": main_ipcr,
        "claim_count": claim_count,
        "primary_cpc_codes": primary_cpc_codes,
        "further_cpc_codes": _coerce_list(record.get("further_cpc_codes")),
        "ipc_codes": ipc_codes,
        "assignee_names": _coerce_list(record.get("assignee_names", record.get("assignees"))),
        "cited_patent_ids": _coerce_list(record.get("cited_patent_ids", record.get("cited_patents"))),
        "npl_citations": _coerce_list(record.get("npl_citations")),
        "related_application_numbers": _coerce_list(record.get("related_application_numbers")),
        "cpc_labels": cpc_labels,
        "ipcr_labels": ipcr_labels,
        "cited_patents": _coerce_list(record.get("cited_patents", record.get("cited_patent_ids"))),
        "inventor_list": _coerce_inventors(record.get("inventor_list", record.get("inventors"))),
    }
    return {field: normalized[field] for field in HF_FIELD_NAMES}


def split_for_date(publication_date: str | None) -> str:
    if publication_date is None or len(publication_date) < 4:
        return "unspecified"
    try:
        year = int(publication_date[:4])
    except ValueError:
        return "unspecified"
    return "train" if year < 2025 else "validation" if year == 2025 else "test"


def release_record_key(record: Mapping[str, Any]) -> bytes:
    """Return a stable identity for global deduplication of append-only JSONL."""
    identifiers = (
        record.get("document_type") or "unknown",
        record.get("patent_grant_id") or "",
        record.get("application_number") or "",
        record.get("publication_date") or "",
    )
    if any(identifiers[1:]):
        material = "\x1f".join(identifiers)
    else:
        material = "\x1f".join(
            (
                identifiers[0],
                record.get("invention_title") or "",
                record.get("source_file") or "",
            )
        )
    return hashlib.sha256(material.encode("utf-8")).digest()


def _serialized_size(record: Mapping[str, Any]) -> int:
    return len(json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


class _SplitShardWriter:
    def __init__(self, output_dir: Path, split: str, *, max_shard_bytes: int, row_group_bytes: int) -> None:
        self.output_dir, self.split = output_dir, split
        self.max_shard_bytes, self.row_group_bytes = max_shard_bytes, row_group_bytes
        self.schema = hf_arrow_schema()
        self.pa, self.pq = _require_pyarrow()
        self.rows: list[dict[str, Any]] = []
        self.pending_bytes = 0
        self.writer: Any | None = None
        self.current_path: Path | None = None
        self.shard_index = 0

    @property
    def shard_count(self) -> int:
        return self.shard_index

    def add(self, record: dict[str, Any]) -> None:
        self.rows.append(record)
        self.pending_bytes += _serialized_size(record)
        if self.pending_bytes >= self.row_group_bytes:
            self.flush()

    def _open_shard(self) -> None:
        directory = self.output_dir / "data" / self.split
        directory.mkdir(parents=True, exist_ok=True)
        self.current_path = directory / f"part-{self.shard_index:05d}.parquet"
        self.writer = self.pq.ParquetWriter(
            self.current_path, self.schema, compression="zstd", use_dictionary=True, write_statistics=True
        )
        self.shard_index += 1

    def flush(self) -> None:
        if not self.rows:
            return
        if self.writer is None:
            self._open_shard()
        table = self.pa.Table.from_pylist(self.rows, schema=self.schema)
        self.writer.write_table(table, row_group_size=len(self.rows))
        self.rows, self.pending_bytes = [], 0
        if self.current_path is not None and self.current_path.stat().st_size >= self.max_shard_bytes:
            self._close_shard()

    def _close_shard(self) -> None:
        if self.writer is not None:
            self.writer.close()
        self.writer, self.current_path = None, None

    def close(self) -> None:
        self.flush()
        self._close_shard()


def _iter_jsonl(
    path: Path,
    *,
    max_records: int | None = None,
    invalid_json_rows: list[dict[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    yielded = 0
    with path.open("rb") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                text = line.decode("utf-8")
            except UnicodeDecodeError as exc:
                if invalid_json_rows is not None:
                    invalid_json_rows.append({"line": line_number, "error": f"Invalid UTF-8: {exc.reason}"})
                    continue
                raise ReleaseValidationError(f"Invalid UTF-8 at {path}:{line_number}: {exc.reason}") from exc
            try:
                raw = json.loads(text)
            except json.JSONDecodeError as exc:
                if invalid_json_rows is not None:
                    invalid_json_rows.append({"line": line_number, "error": exc.msg})
                    continue
                raise ReleaseValidationError(f"Invalid JSON at {path}:{line_number}: {exc.msg}") from exc
            if not isinstance(raw, Mapping):
                if invalid_json_rows is not None:
                    invalid_json_rows.append({"line": line_number, "error": "Expected an object."})
                    continue
                raise ReleaseValidationError(f"Expected an object at {path}:{line_number}.")
            yield normalize_record(raw)
            yielded += 1
            if max_records is not None and yielded >= max_records:
                return


def assert_manifest_complete(data_root: Path) -> None:
    manifest_path = data_root / "manifest.json"
    if not manifest_path.exists():
        return
    non_complete = [entry for entry in IngestManifest.load(manifest_path).files.values() if entry.status != "complete"]
    if non_complete:
        names = ", ".join(Path(entry.path).name for entry in non_complete[:5])
        raise ReleaseReadinessError(
            f"Release blocked: {len(non_complete)} source file(s) are not complete ({names})."
        )


def _required_free_space(source_bytes: int, expected_compression_ratio: float) -> int:
    if not 0 < expected_compression_ratio <= 1:
        raise ValueError("expected_compression_ratio must be in the interval (0, 1].")
    estimated_output_bytes = math.ceil(source_bytes * expected_compression_ratio)
    return max(MIN_FREE_SPACE_BYTES, math.ceil(estimated_output_bytes * OUTPUT_HEADROOM_MULTIPLIER))


def _check_output_space(source_path: Path, output_dir: Path, *, max_records: int | None, expected_compression_ratio: float) -> None:
    target = output_dir.parent if output_dir.parent.exists() else Path.cwd()
    free_bytes = shutil.disk_usage(target).free
    required = MIN_FREE_SPACE_BYTES if max_records is not None else _required_free_space(
        source_path.stat().st_size, expected_compression_ratio
    )
    if free_bytes < required:
        raise ReleaseReadinessError(
            f"Release blocked by free-space guard: {free_bytes / 1e9:.1f} GB free, "
            f"{required / 1e9:.1f} GB required. Use another volume or --max-records."
        )


def dataset_card_data_files(records_by_split: Mapping[str, int]) -> str:
    """Emit Hugging Face ``data_files`` entries only for splits that have rows.

    An empty ``unspecified`` glob makes the Hub dataset viewer fail to infer a
    shared file format across splits. Buyers and the public snapshot both need
    the card to mention only shards that exist.
    """
    lines = ["  data_files:"]
    for split in ("train", "validation", "test", "unspecified"):
        if records_by_split.get(split, 0) > 0:
            lines.append(f"  - split: {split}")
            lines.append(f"    path: data/{split}/*.parquet")
    if len(lines) == 1:
        raise ReleaseError("Release card cannot be written because no split contains records.")
    return "\n".join(lines)


def _dataset_card(summary: ReleaseSummary) -> str:
    counts = summary.records_by_split
    data_files = dataset_card_data_files(counts)
    return f'''---
language:
- en
license: other
pretty_name: PatentPulse
tags:
- patents
- uspto
- legal
task_categories:
- text-classification
- summarization
configs:
- config_name: default
{data_files}
---

# PatentPulse

PatentPulse is a provenance-preserving corpus of USPTO grants and published patent applications extracted from official weekly XML bulk releases. This immutable Parquet snapshot normalizes the project's historical append-only JSONL into one schema.

## Release summary

- Input rows: {summary.records_seen:,}; unique released records: {summary.records_written:,}; duplicates removed: {summary.duplicates_skipped:,}; malformed JSON rows skipped: {len(summary.invalid_json_rows):,}
- Splits: train {counts.get("train", 0):,}; validation {counts.get("validation", 0):,}; test {counts.get("test", 0):,}; unspecified {counts.get("unspecified", 0):,}
- Source export: `{summary.source_file}` ({summary.source_bytes:,} bytes)
- Canonical record digest: `{summary.canonical_sha256}`
- Shard target: {summary.max_shard_bytes / 1e9:g} GB (a shard may exceed the target by one 64 MB row group)

## Schema and splits

Every Parquet shard has the same explicit Arrow schema. Canonical `*_text` fields are mirrored by HUPD-compatible aliases (`title`, `abstract`, `claims`, and `full_description`). Classification and citation columns are lists of strings. `source_file` contains only an originating archive filename, never a local path.

The split is temporal: pre-2025 records are `train`, 2025 records are `validation`, 2026-and-later records are `test`, and records without a usable publication year are `unspecified`.

## Provenance, licensing, and responsible use

Records originate from official USPTO public bulk products. Most government-produced material is public domain in the United States, but patent documents can include third-party material and the USPTO reserves international rights. This dataset is marked `other`, not as a blanket open-content license. Users must review USPTO terms, provide source acknowledgement, and assess rights for their jurisdiction and use case.

The corpus is for research and technical-information workflows, not legal validity, infringement, patentability, or freedom-to-operate decisions. `release_manifest.json` records this snapshot's counts, shard settings, and canonical digest; the upstream manifest records source URLs, checksums, and parse failures.
'''


def _data_rights_notice() -> str:
    """Return the self-contained data-rights notice shipped with every snapshot."""
    return '''# PatentPulse data rights and reuse notice

This snapshot is a normalized, machine-readable representation of public USPTO
patent grants and published patent applications. It uses Hugging Face's `other`
license label. The repository-level MIT license for PatentPulse source code and
documentation does not grant rights in underlying patent-document content.

PatentPulse imposes no additional non-commercial, no-derivatives, or no-training
restriction. In the United States, the USPTO says most government-produced
material is public domain and may be copied and distributed with appropriate
acknowledgement. Subject to applicable law and third-party rights, users may
copy, transform, redistribute, index, analyze, and use this snapshot for
machine-learning research and training.

Patent documents can include applicant-authored text, figures, incorporated
material, and other content that may be protected by copyright or other rights.
The USPTO reserves the right to assert copyright protection internationally.
PatentPulse cannot grant rights in that material. Users must assess rights for
their jurisdiction and use case, retain this notice when redistributing, and
acknowledge: "Source: United States Patent and Trademark Office (USPTO),
processed by PatentPulse."

Do not imply USPTO endorsement or use USPTO marks. The data is provided as-is
and is not legal advice or proof of validity, infringement, freedom to operate,
patentability, ownership, or enforceability. See the USPTO Terms of Use:
https://www.uspto.gov/terms-use-uspto-websites
'''


def build_release(
    input_path: Path,
    output_dir: Path,
    *,
    data_root: Path | None = None,
    max_shard_bytes: int = DEFAULT_MAX_SHARD_BYTES,
    row_group_bytes: int = DEFAULT_ROW_GROUP_BYTES,
    max_records: int | None = None,
    expected_compression_ratio: float = DEFAULT_EXPECTED_COMPRESSION_RATIO,
    skip_invalid_json: bool = False,
) -> ReleaseSummary:
    """Build a non-destructive Parquet release from a JSONL snapshot."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Input JSONL not found: {input_path}")
    if max_shard_bytes <= 0 or row_group_bytes <= 0:
        raise ValueError("Shard and row-group sizes must be positive.")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ReleaseError(f"Output directory is not empty: {output_dir}")
    if data_root is not None:
        assert_manifest_complete(data_root)
    _check_output_space(input_path, output_dir, max_records=max_records, expected_compression_ratio=expected_compression_ratio)

    output_dir.mkdir(parents=True, exist_ok=True)
    writers: dict[str, _SplitShardWriter] = {}
    digest, records_by_split = hashlib.sha256(), Counter[str]()
    seen_keys: set[bytes] = set()
    records_seen = 0
    duplicates_skipped = 0
    invalid_json_rows: list[dict[str, Any]] | None = [] if skip_invalid_json else None
    try:
        for record in _iter_jsonl(
            input_path,
            max_records=max_records,
            invalid_json_rows=invalid_json_rows,
        ):
            records_seen += 1
            key = release_record_key(record)
            if key in seen_keys:
                duplicates_skipped += 1
                continue
            seen_keys.add(key)
            split = split_for_date(record["publication_date"])
            writer = writers.setdefault(split, _SplitShardWriter(
                output_dir, split, max_shard_bytes=max_shard_bytes, row_group_bytes=row_group_bytes
            ))
            writer.add(record)
            digest.update(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
            digest.update(b"\n")
            records_by_split[split] += 1
    finally:
        for writer in writers.values():
            writer.close()

    summary = ReleaseSummary(
        created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        source_file=input_path.name,
        source_bytes=input_path.stat().st_size,
        records_seen=records_seen,
        records_written=sum(records_by_split.values()),
        duplicates_skipped=duplicates_skipped,
        invalid_json_rows=invalid_json_rows or [],
        records_by_split=dict(sorted(records_by_split.items())),
        shards_by_split={split: writer.shard_count for split, writer in sorted(writers.items())},
        canonical_sha256=digest.hexdigest(),
        max_shard_bytes=max_shard_bytes,
    )
    (output_dir / "release_manifest.json").write_text(json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(_dataset_card(summary), encoding="utf-8")
    (output_dir / "DATA_LICENSE.md").write_text(_data_rights_notice(), encoding="utf-8")
    validate_release(output_dir, max_shard_bytes=max_shard_bytes)
    return summary


def validate_release(output_dir: Path, *, max_shard_bytes: int = DEFAULT_MAX_SHARD_BYTES) -> ReleaseSummary:
    """Verify a release's metadata, schema, aliases, record counts, and path safety."""
    _, pq = _require_pyarrow()
    readme, manifest_path = output_dir / "README.md", output_dir / "release_manifest.json"
    if not readme.is_file() or not readme.read_text(encoding="utf-8").startswith("---\n"):
        raise ReleaseValidationError("Release README.md must start with Hugging Face YAML metadata.")
    if not manifest_path.is_file():
        raise ReleaseValidationError("Release is missing release_manifest.json.")
    data_license = output_dir / "DATA_LICENSE.md"
    if not data_license.is_file() or "machine-learning research and training" not in data_license.read_text(encoding="utf-8"):
        raise ReleaseValidationError("Release is missing the required data-rights notice.")
    summary = ReleaseSummary(**json.loads(manifest_path.read_text(encoding="utf-8")))
    files = sorted((output_dir / "data").glob("*/*.parquet"))
    if not files:
        raise ReleaseValidationError("Release contains no Parquet shards.")
    expected_schema, records_by_split = hf_arrow_schema(), Counter[str]()
    for path in files:
        # Parquet row groups are atomic. The writer closes a shard after a
        # completed row group reaches the target, so the final file can exceed
        # that target by at most one row group.
        if path.stat().st_size > max_shard_bytes + DEFAULT_ROW_GROUP_BYTES:
            raise ReleaseValidationError(f"Shard exceeds configured limit plus row-group allowance: {path}")
        parquet = pq.ParquetFile(path)
        if not parquet.schema_arrow.equals(expected_schema, check_metadata=False):
            raise ReleaseValidationError(f"Schema mismatch in {path}")
        records_by_split[path.parent.name] += parquet.metadata.num_rows
        for batch in parquet.iter_batches(batch_size=8_192, columns=(
            "patent_grant_id", "patent_number", "publication_number", "invention_title", "title",
            "abstract_text", "abstract", "claims_text", "claims", "description_text", "full_description", "source_file",
        )):
            columns = {name: batch.column(index).to_pylist() for index, name in enumerate(batch.schema.names)}
            for index, source_file in enumerate(columns["source_file"]):
                if source_file and any(token in source_file for token in ("/", "\\", ":")):
                    raise ReleaseValidationError(f"Local path leaked in {path} row {index}.")
                for canonical, alias in (
                    ("patent_grant_id", "patent_number"), ("patent_grant_id", "publication_number"),
                    ("invention_title", "title"), ("abstract_text", "abstract"),
                    ("claims_text", "claims"), ("description_text", "full_description"),
                ):
                    if columns[canonical][index] != columns[alias][index]:
                        raise ReleaseValidationError(f"Alias mismatch in {path} row {index}: {alias}")
    if sum(records_by_split.values()) != summary.records_written:
        raise ReleaseValidationError("Release manifest record count does not match Parquet files.")
    if dict(sorted(records_by_split.items())) != dict(sorted(summary.records_by_split.items())):
        raise ReleaseValidationError("Release manifest split counts do not match Parquet files.")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Hugging Face-ready PatentPulse Parquet release.")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Normalize JSONL into validated Parquet shards.")
    export.add_argument("--input", type=Path, default=Path("data/processed/patents.jsonl"))
    export.add_argument("--output", type=Path, default=Path("data/hf-release"))
    export.add_argument("--data-root", type=Path, default=Path("data"))
    export.add_argument("--max-shard-size-gb", type=float, default=5.0)
    export.add_argument("--row-group-size-mb", type=float, default=64.0)
    export.add_argument("--max-records", type=int, default=None, help="Bounded validation export; not a publishable full release.")
    export.add_argument("--expected-compression-ratio", type=float, default=DEFAULT_EXPECTED_COMPRESSION_RATIO)
    export.add_argument(
        "--skip-invalid-json",
        action="store_true",
        help="Skip malformed JSONL rows and record their line numbers in release_manifest.json.",
    )
    validate = commands.add_parser("validate", help="Validate an existing Parquet release.")
    validate.add_argument("--release", type=Path, default=Path("data/hf-release"))
    validate.add_argument("--max-shard-size-gb", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        if args.command == "export":
            if args.max_records is not None and args.max_records <= 0:
                raise ValueError("--max-records must be positive.")
            summary = build_release(
                args.input, args.output, data_root=args.data_root,
                max_shard_bytes=round(args.max_shard_size_gb * 1e9),
                row_group_bytes=round(args.row_group_size_mb * 1e6),
                max_records=args.max_records, expected_compression_ratio=args.expected_compression_ratio,
                skip_invalid_json=args.skip_invalid_json,
            )
        else:
            summary = validate_release(args.release, max_shard_bytes=round(args.max_shard_size_gb * 1e9))
    except (OSError, ValueError, ReleaseError) as exc:
        print(f"Release failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(summary), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
