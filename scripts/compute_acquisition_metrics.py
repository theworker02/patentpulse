#!/usr/bin/env python3
"""Compute acquisition-grade corpus metrics from the published Hugging Face snapshot.

Requires network access to huggingface.co. Downloads only the release manifest
plus a small number of Parquet footers / row groups.

Example:
  python scripts/compute_acquisition_metrics.py --output docs/acquisition/metrics/acquisition_metrics.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _require_deps():
    try:
        from huggingface_hub import HfApi, hf_hub_download
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Install huggingface_hub and pyarrow to compute published-corpus metrics."
        ) from exc
    return HfApi, hf_hub_download, pa, pc, pq


def _parquet_column_sizes(path: Path, pq) -> tuple[int, int, int]:
    pf = pq.ParquetFile(path)
    uncompressed = compressed = 0
    for rg_index in range(pf.metadata.num_row_groups):
        row_group = pf.metadata.row_group(rg_index)
        for col_index in range(row_group.num_columns):
            column = row_group.column(col_index)
            uncompressed += column.total_uncompressed_size
            compressed += column.total_compressed_size
    return uncompressed, compressed, pf.metadata.num_rows


def _nonempty_string_pct(table, field: str, pc, pa) -> float:
    col = table[field]
    filled = pc.fill_null(col, "")
    nonempty = int(pc.sum(pc.invert(pc.equal(filled, "")).cast(pa.int64())).as_py())
    return round(100.0 * nonempty / table.num_rows, 3)


def _nonempty_list_pct(table, field: str, pc, pa) -> float:
    col = table[field]
    lengths = pc.fill_null(pc.list_value_length(col), 0)
    nonempty = int(pc.sum(pc.greater(lengths, 0).cast(pa.int64())).as_py())
    return round(100.0 * nonempty / table.num_rows, 3)


def _text_length_stats(table, field: str) -> dict[str, Any]:
    values = [len(value) if value else 0 for value in table[field].to_pylist()]
    nonzero = sorted(value for value in values if value > 0)
    if not nonzero:
        return {"coverage_pct": 0.0}
    def percentile(p: float) -> int:
        return nonzero[int((len(nonzero) - 1) * p)]
    return {
        "coverage_pct": round(100.0 * len(nonzero) / len(values), 3),
        "mean_chars": round(sum(nonzero) / len(nonzero), 1),
        "p50_chars": percentile(0.5),
        "p90_chars": percentile(0.9),
        "p99_chars": percentile(0.99),
        "max_chars": nonzero[-1],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="theworker02/patentpulse")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--sample-row-groups",
        type=int,
        default=20,
        help="Row groups to sample from train/validation shards for field fill rates",
    )
    args = parser.parse_args()

    HfApi, hf_hub_download, pa, pc, pq = _require_deps()
    api = HfApi()

    manifest_path = Path(
        hf_hub_download(args.repo, "release_manifest.json", repo_type="dataset")
    )
    release = json.loads(manifest_path.read_text(encoding="utf-8"))
    invalid_rows = release.get("invalid_json_rows") or []
    invalid_by_prefix = Counter(
        str(item.get("error", "unknown")).split(":")[0] for item in invalid_rows
    )

    tree = list(api.list_repo_tree(args.repo, repo_type="dataset", recursive=True))
    parquet_files = []
    hub_bytes = 0
    for item in tree:
        path = getattr(item, "path", None) or getattr(item, "rfilename", "")
        size = getattr(item, "size", None) or 0
        hub_bytes += size
        if path.endswith(".parquet"):
            parquet_files.append({"path": path, "size_bytes": size})

    size_samples = []
    for relative in (
        "data/train/part-00000.parquet",
        "data/validation/part-00005.parquet",
        "data/test/part-00003.parquet",
    ):
        local = Path(hf_hub_download(args.repo, relative, repo_type="dataset"))
        uncompressed, compressed, rows = _parquet_column_sizes(local, pq)
        size_samples.append(
            {
                "path": relative,
                "rows": rows,
                "uncompressed_bytes": uncompressed,
                "compressed_bytes_meta": compressed,
                "compression_ratio": round(compressed / uncompressed, 4) if uncompressed else None,
            }
        )

    sample_rows = sum(item["rows"] for item in size_samples)
    sample_uncompressed = sum(item["uncompressed_bytes"] for item in size_samples)
    bytes_per_row = sample_uncompressed / sample_rows if sample_rows else 0.0
    records_written = int(release["records_written"])
    estimated_parquet_uncompressed = int(bytes_per_row * records_written)

    # Field completeness sample
    train_path = Path(
        hf_hub_download(args.repo, "data/train/part-00000.parquet", repo_type="dataset")
    )
    val_path = Path(
        hf_hub_download(args.repo, "data/validation/part-00000.parquet", repo_type="dataset")
    )
    tables = []
    for path in (train_path, val_path):
        pf = pq.ParquetFile(path)
        step = max(1, pf.metadata.num_row_groups // args.sample_row_groups)
        indices = list(range(0, pf.metadata.num_row_groups, step))[: args.sample_row_groups]
        tables.extend(pf.read_row_group(index) for index in indices)
    sample = pa.concat_tables(tables)

    string_fields = [
        "patent_grant_id",
        "application_number",
        "publication_date",
        "invention_title",
        "abstract_text",
        "claims_text",
        "description_text",
        "document_type",
        "kind_code",
        "filing_date",
        "main_cpc_label",
        "source_file",
    ]
    list_fields = [
        "primary_cpc_codes",
        "further_cpc_codes",
        "ipc_codes",
        "assignee_names",
        "cited_patent_ids",
        "inventor_list",
        "cpc_labels",
        "npl_citations",
    ]
    field_fill = {
        field: {"nonempty_pct": _nonempty_string_pct(sample, field, pc, pa)}
        for field in string_fields
        if field in sample.column_names
    }
    field_fill.update(
        {
            field: {"nonempty_list_pct": _nonempty_list_pct(sample, field, pc, pa)}
            for field in list_fields
            if field in sample.column_names
        }
    )
    text_stats = {
        field: _text_length_stats(sample, field)
        for field in ("invention_title", "abstract_text", "claims_text", "description_text")
    }

    doc_types = Counter(sample["document_type"].to_pylist())
    years = Counter((value or "")[:4] for value in sample["publication_date"].to_pylist())

    records_seen = int(release["records_seen"])
    duplicates_skipped = int(release["duplicates_skipped"])
    invalid_count = len(invalid_rows)

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_repo": args.repo,
        "release": {
            "created_at": release.get("created_at"),
            "canonical_sha256": release.get("canonical_sha256"),
            "records_seen": records_seen,
            "records_written": records_written,
            "duplicates_skipped": duplicates_skipped,
            "invalid_json_rows": invalid_count,
            "records_by_split": release.get("records_by_split"),
            "shards_by_split": release.get("shards_by_split"),
            "source_file": release.get("source_file"),
            "source_bytes_jsonl": release.get("source_bytes"),
            "max_shard_bytes": release.get("max_shard_bytes"),
        },
        "dedup_and_errors": {
            "duplicate_rate_vs_seen": round(duplicates_skipped / records_seen, 6) if records_seen else None,
            "duplicate_pct": round(100.0 * duplicates_skipped / records_seen, 4) if records_seen else None,
            "invalid_json_rate_vs_seen": round(invalid_count / records_seen, 9) if records_seen else None,
            "invalid_json_pct": round(100.0 * invalid_count / records_seen, 6) if records_seen else None,
            "invalid_json_by_error_prefix": dict(invalid_by_prefix),
            "yield_unique_vs_seen": round(records_written / records_seen, 6) if records_seen else None,
        },
        "corpus_sizes": {
            "hub_total_bytes": hub_bytes,
            "hub_total_GB": round(hub_bytes / 1e9, 3),
            "hub_total_GiB": round(hub_bytes / (1024**3), 3),
            "parquet_file_count": len(parquet_files),
            "jsonl_source_bytes": release.get("source_bytes"),
            "jsonl_source_GB": round(release["source_bytes"] / 1e9, 3),
            "estimated_parquet_uncompressed_bytes": estimated_parquet_uncompressed,
            "estimated_parquet_uncompressed_GB": round(estimated_parquet_uncompressed / 1e9, 3),
            "estimated_parquet_uncompressed_GiB": round(estimated_parquet_uncompressed / (1024**3), 3),
            "compression_ratio_hub_vs_jsonl": round(hub_bytes / release["source_bytes"], 4),
            "compression_ratio_hub_vs_est_parquet_u": round(
                hub_bytes / estimated_parquet_uncompressed, 4
            ),
            "bytes_per_row_uncompressed_sample": round(bytes_per_row, 1),
            "size_samples": size_samples,
            "methodology": (
                "Hub compressed size sums Hugging Face tree file sizes. "
                "Parquet uncompressed size extrapolates average uncompressed bytes/row "
                "from three representative shards' footers. JSONL source_bytes comes from "
                "release_manifest.json."
            ),
        },
        "quality_sample": {
            "rows_sampled": sample.num_rows,
            "document_type_counts": dict(doc_types),
            "publication_year_counts": dict(sorted(years.items())),
            "field_fill": field_fill,
            "text_length_stats": text_stats,
            "caveats": [
                "Sampled row groups from train part-00000 and validation part-00000; not a full-corpus census.",
                "Published snapshot may omit bibliographic fields that the current extractor populates "
                "(kind_code, filing_date, inventors, assignees, citations) when historical JSONL rows "
                "predated those fields. Re-ingest + re-export recovers them.",
                "Design/plant patents commonly lack abstracts and CPC labels; that is expected source sparsity.",
            ],
        },
    }

    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
