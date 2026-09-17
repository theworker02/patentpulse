"""Inspect one PatentPulse JSONL record."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/processed/patents.jsonl")
    if not path.exists():
        print(f"Missing {path}")
        return 1
    with path.open("r", encoding="utf-8") as handle:
        line = handle.readline()
    if not line:
        print(f"{path} is empty")
        return 1
    record = json.loads(line)
    keys = [
        "patent_grant_id",
        "application_number",
        "publication_date",
        "title",
        "abstract",
        "main_cpc_label",
        "cpc_labels",
        "document_type",
        "claim_count",
        "inventor_list",
        "assignee_names",
    ]
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and len(value) > 180:
            value = value[:177] + "..."
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
