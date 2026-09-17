"""Ingestion manifest — tracks which source files have been processed."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class FileEntry:
    path: str
    status: str = "pending"
    records_parsed: int = 0
    records_written: int = 0
    records_failed: int = 0
    sha256: str | None = None
    source_url: str | None = None
    ingested_at: str | None = None
    error: str | None = None
    started_at: str | None = None


@dataclass
class IngestManifest:
    version: int = 1
    updated_at: str = field(default_factory=_utc_now)
    files: dict[str, FileEntry] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> IngestManifest:
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        files = {
            key: FileEntry(**value)
            for key, value in payload.get("files", {}).items()
        }
        return cls(
            version=payload.get("version", 1),
            updated_at=payload.get("updated_at", _utc_now()),
            files=files,
        )

    def save(self, path: Path) -> None:
        """Atomically persist the manifest so interruptions cannot truncate it."""
        self.updated_at = _utc_now()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "version": self.version,
            "updated_at": self.updated_at,
            "files": {key: asdict(entry) for key, entry in self.files.items()},
        }
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, file_key: str) -> FileEntry | None:
        return self.files.get(file_key)

    def mark_running(self, file_key: str, *, path: str, source_url: str | None = None) -> None:
        entry = self.files.get(file_key) or FileEntry(path=path, source_url=source_url)
        entry.status = "running"
        entry.records_parsed = 0
        entry.records_written = 0
        entry.records_failed = 0
        entry.sha256 = None
        entry.error = None
        entry.started_at = _utc_now()
        if source_url is not None:
            entry.source_url = source_url
        self.files[file_key] = entry

    def recover_stale_runs(
        self,
        *,
        stale_after: timedelta = timedelta(hours=6),
    ) -> list[FileEntry]:
        """Return abandoned ``running`` entries to the retryable pending state."""
        now = datetime.now(timezone.utc)
        recovered: list[FileEntry] = []
        for entry in self.files.values():
            if entry.status != "running":
                continue
            started = None
            if entry.started_at:
                try:
                    started = datetime.fromisoformat(entry.started_at)
                except ValueError:
                    started = None
            if started is None or now - started >= stale_after:
                entry.status = "pending"
                entry.error = "Recovered an abandoned ingestion attempt."
                entry.started_at = None
                recovered.append(entry)
        return recovered

    def mark_complete(
        self,
        file_key: str,
        *,
        records_parsed: int,
        records_written: int,
        records_failed: int,
        sha256: str | None = None,
    ) -> None:
        entry = self.files[file_key]
        entry.status = "complete"
        entry.records_parsed = records_parsed
        entry.records_written = records_written
        entry.records_failed = records_failed
        entry.sha256 = sha256
        entry.ingested_at = _utc_now()
        entry.started_at = None

    def mark_failed(self, file_key: str, error: str) -> None:
        entry = self.files[file_key]
        entry.status = "failed"
        entry.error = error
        entry.ingested_at = _utc_now()
        entry.started_at = None

    def pending_files(self) -> list[FileEntry]:
        return [entry for entry in self.files.values() if entry.status in {"pending", "failed"}]

    def summary(self) -> dict[str, int]:
        complete = [entry for entry in self.files.values() if entry.status == "complete"]
        return {
            "files_total": len(self.files),
            "files_complete": len(complete),
            "files_pending": sum(entry.status == "pending" for entry in self.files.values()),
            "files_running": sum(entry.status == "running" for entry in self.files.values()),
            "files_failed": sum(entry.status == "failed" for entry in self.files.values()),
            "records_parsed": sum(entry.records_parsed for entry in complete),
            "records_written": sum(entry.records_written for entry in complete),
            "records_failed": sum(entry.records_failed for entry in complete),
        }
