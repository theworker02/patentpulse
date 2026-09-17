"""Orchestrate USPTO source download and database ingestion."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from patentpulse.download import (
    download_odp_file,
    download_url,
    list_odp_product_files,
    resolve_api_key,
    sha256_file,
)
from patentpulse.manifest import FileEntry, IngestManifest
from patentpulse.parse import parse_bulk_file
from patentpulse.sources import (
    APPLICATION_FULLTEXT,
    BDSS_BASE_URL,
    GRANT_FULLTEXT,
    SourceKind,
    bdss_file_url,
)

LOGGER = logging.getLogger("patentpulse.ingest")

DEFAULT_DATA_ROOT = Path("data")
RAW_DIR = DEFAULT_DATA_ROOT / "raw"
PROCESSED_DIR = DEFAULT_DATA_ROOT / "processed"
MANIFEST_PATH = DEFAULT_DATA_ROOT / "manifest.json"
DEFAULT_DB_PATH = PROCESSED_DIR / "patents.db"
DEFAULT_JSONL_PATH = PROCESSED_DIR / "patents.jsonl"

SUPPORTED_EXTENSIONS = {".xml", ".zip", ".tar", ".gz"}
RAW_ARCHIVE_DELETE_RETRIES = 6
RAW_ARCHIVE_DELETE_RETRY_DELAY_SECONDS = 5
INGEST_LOCK_NAME = ".ingest.lock"
INGEST_LOCK_STALE_AFTER = timedelta(hours=12)
MAX_SYNC_FETCH_ERRORS = 5


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


@contextmanager
def _ingestion_lock(data_root: Path):
    """Serialize local ingestion and recover locks left by dead processes."""
    data_root.mkdir(parents=True, exist_ok=True)
    lock_path = data_root / INGEST_LOCK_NAME
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    for attempt in range(2):
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(descriptor, json.dumps(payload).encode("utf-8"))
            finally:
                os.close(descriptor)
            break
        except FileExistsError:
            stale = False
            try:
                lock_payload = json.loads(lock_path.read_text(encoding="utf-8"))
                owner_pid = int(lock_payload["pid"])
                try:
                    os.kill(owner_pid, 0)
                    owner_alive = True
                except ProcessLookupError:
                    owner_alive = False
                except PermissionError:
                    owner_alive = True
                except OSError:
                    owner_alive = False
                started_at = datetime.fromisoformat(lock_payload["started_at"])
                stale = (
                    not owner_alive
                    or datetime.now(timezone.utc) - started_at >= INGEST_LOCK_STALE_AFTER
                )
            except (OSError, KeyError, TypeError, ValueError):
                try:
                    stale = (
                        datetime.now(timezone.utc)
                        - datetime.fromtimestamp(lock_path.stat().st_mtime, timezone.utc)
                        >= INGEST_LOCK_STALE_AFTER
                    )
                except OSError:
                    stale = True
            if not stale or attempt:
                raise RuntimeError(
                    f"Another ingestion process appears active: {lock_path}"
                )
            LOGGER.warning("Removing stale ingestion lock: %s", lock_path)
            lock_path.unlink(missing_ok=True)
    else:  # pragma: no cover - loop always either acquires or raises
        raise RuntimeError(f"Unable to acquire ingestion lock: {lock_path}")

    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _recover_stale_manifest_runs(data_root: Path) -> None:
    manifest_path = data_root / "manifest.json"
    manifest = IngestManifest.load(manifest_path)
    recovered = manifest.recover_stale_runs()
    if recovered:
        manifest.save(manifest_path)
        LOGGER.warning("Recovered %s abandoned ingestion attempt(s)", len(recovered))


def _ensure_workspace(data_root: Path) -> None:
    (data_root / "raw" / "grants").mkdir(parents=True, exist_ok=True)
    (data_root / "raw" / "applications").mkdir(parents=True, exist_ok=True)
    (data_root / "processed").mkdir(parents=True, exist_ok=True)
    manifest_path = data_root / "manifest.json"
    if not manifest_path.exists():
        IngestManifest().save(manifest_path)


def init_workspace(data_root: Path = DEFAULT_DATA_ROOT) -> None:
    """Create the local data layout used for ingestion and seed the fixture."""
    _ensure_workspace(data_root)

    manifest_path = data_root / "manifest.json"
    if not manifest_path.exists():
        IngestManifest().save(manifest_path)

    bootstrap = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_bulk.xml"
    target = data_root / "raw" / "bootstrap_sample_bulk.xml"
    if bootstrap.exists() and not target.exists():
        shutil.copyfile(bootstrap, target)
        LOGGER.info("Seeded bootstrap source: %s", target)


def discover_local_sources(raw_dir: Path) -> list[Path]:
    """Find ingestible XML/ZIP files under ``data/raw``."""
    files: list[Path] = []
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS or path.name.endswith(".tar.gz"):
            files.append(path)
    return files


def ingest_local_file(
    source_path: Path,
    *,
    data_root: Path,
    output_format: str = "both",
    limit: int | None = None,
    force: bool = False,
) -> dict[str, int]:
    """Parse one local bulk file into the processed dataset."""
    manifest_path = data_root / "manifest.json"
    manifest = IngestManifest.load(manifest_path)
    file_key = str(source_path.resolve())

    existing = manifest.get(file_key)
    if existing and existing.status == "complete" and not force:
        LOGGER.info("Skipping already ingested file: %s", source_path)
        return {
            "documents_parsed": existing.records_parsed,
            "records_written": existing.records_written,
            "documents_failed": existing.records_failed,
            "skipped": 1,
        }

    manifest.mark_running(file_key, path=file_key, source_url=None)
    manifest.save(manifest_path)

    output_base = data_root / "processed" / "patents"
    try:
        stats = parse_bulk_file(
            source_path,
            output_base,
            output_format=output_format,
            limit=limit,
        )
        digest = sha256_file(source_path)
        manifest.mark_complete(
            file_key,
            records_parsed=stats["documents_parsed"],
            records_written=stats["records_written"],
            records_failed=stats["documents_failed"],
            sha256=digest,
        )
        manifest.save(manifest_path)
        return stats
    except Exception as exc:
        manifest.mark_failed(file_key, str(exc))
        manifest.save(manifest_path)
        raise


def _run_local_ingest(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    output_format: str = "both",
    limit: int | None = None,
    force: bool = False,
) -> dict[str, int]:
    """Ingest all pending files discovered under ``data/raw``."""
    raw_dir = data_root / "raw"
    totals = {
        "files_processed": 0,
        "documents_parsed": 0,
        "records_written": 0,
        "documents_failed": 0,
        "files_skipped": 0,
        "files_failed": 0,
    }

    for source_path in discover_local_sources(raw_dir):
        LOGGER.info("Ingesting %s", source_path)
        try:
            stats = ingest_local_file(
                source_path,
                data_root=data_root,
                output_format=output_format,
                limit=limit,
                force=force,
            )
        except Exception as exc:
            totals["files_failed"] += 1
            LOGGER.exception("Failed to ingest %s: %s", source_path, exc)
            continue
        if stats.get("skipped"):
            totals["files_skipped"] += 1
            continue
        totals["files_processed"] += 1
        totals["documents_parsed"] += stats.get("documents_parsed", 0)
        totals["records_written"] += stats.get("records_written", 0)
        totals["documents_failed"] += stats.get("documents_failed", 0)

    return totals


def run_local_ingest(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    output_format: str = "both",
    limit: int | None = None,
    force: bool = False,
) -> dict[str, int]:
    """Ingest local sources under a process lock with stale-run recovery."""
    _ensure_workspace(data_root)
    with _ingestion_lock(data_root):
        _recover_stale_manifest_runs(data_root)
        return _run_local_ingest(
            data_root=data_root,
            output_format=output_format,
            limit=limit,
            force=force,
        )


def _ingested_filenames(data_root: Path) -> set[str]:
    manifest = IngestManifest.load(data_root / "manifest.json")
    return {
        Path(entry.path).name
        for entry in manifest.files.values()
        if entry.status == "complete"
    }


def _is_archive_path(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".gz"))


def remove_raw_archive_after_ingest(source_path: Path) -> bool:
    """Remove a completed archive without letting a transient Windows lock stop sync.

    ZIP readers, antivirus scanning, and cloud-sync clients can retain a short-lived
    handle after parsing. The manifest has already been marked complete at this
    point, so retaining an archive is preferable to aborting the remaining backfill.
    """
    for attempt in range(1, RAW_ARCHIVE_DELETE_RETRIES + 1):
        try:
            source_path.unlink()
            LOGGER.info("Removed raw archive %s after ingest", source_path.name)
            return True
        except FileNotFoundError:
            return True
        except PermissionError as exc:
            if attempt == RAW_ARCHIVE_DELETE_RETRIES:
                LOGGER.warning(
                    "Keeping completed raw archive %s because it remains locked: %s",
                    source_path.name,
                    exc,
                )
                return False
            LOGGER.warning(
                "Raw archive %s is still locked; retrying deletion (%s/%s)",
                source_path.name,
                attempt,
                RAW_ARCHIVE_DELETE_RETRIES,
            )
            time.sleep(RAW_ARCHIVE_DELETE_RETRY_DELAY_SECONDS)

    return False


_ODP_FILE_CACHE: dict[str, list] = {}


def fetch_from_odp(
    *,
    product_id: str,
    data_root: Path,
    api_key: str,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 1,
    overwrite: bool = False,
    skip_existing: bool = True,
    exclude_filenames: set[str] | None = None,
) -> list[Path]:
    """Download weekly bulk files, skipping dumps already ingested."""
    cache_key = f"{product_id}:{from_date}:{to_date}"
    files = _ODP_FILE_CACHE.get(cache_key)
    if files is None:
        files = list_odp_product_files(
            product_id,
            api_key=api_key,
            from_date=from_date,
            to_date=to_date,
            limit=None,
        )
        if files:
            _ODP_FILE_CACHE[cache_key] = files
    if not files:
        LOGGER.warning("No ODP files currently available for product %s.", product_id)
        return []

    downloaded: list[Path] = []
    kind_dir = "grants" if product_id == GRANT_FULLTEXT.odp_product_id else "applications"
    target_dir = data_root / "raw" / kind_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest = IngestManifest.load(data_root / "manifest.json")
    already = _ingested_filenames(data_root) if skip_existing else set()
    excluded = exclude_filenames or set()
    skipped = 0

    for file_info in files:
        if len(downloaded) >= limit:
            break
        file_name = file_info.get("fileName") or file_info.get("file_name")
        if not file_name or file_name in excluded:
            continue
        destination = target_dir / file_name
        key = str(destination.resolve())
        entry = manifest.files.get(key)
        retry_failed = entry is not None and entry.status == "failed"
        expected_size = file_info.get("fileSize") or file_info.get("file_size")
        try:
            expected_size = int(expected_size) if expected_size is not None else None
        except (TypeError, ValueError):
            expected_size = None

        if skip_existing and file_name in already and not overwrite:
            skipped += 1
            continue
        if skip_existing and destination.exists() and not overwrite and not retry_failed:
            if expected_size is None or destination.stat().st_size == expected_size:
                LOGGER.info("Already on disk, will ingest: %s", destination)
                downloaded.append(destination)
                continue
            LOGGER.warning("Removing incomplete local archive: %s", destination)
            destination.unlink()

        download_uri = file_info.get("fileDownloadURI") or file_info.get("file_download_uri")
        LOGGER.info("Fetching %s (%s bytes)", file_name, expected_size or "unknown")
        try:
            download_odp_file(
                product_id,
                file_name,
                destination,
                api_key=api_key,
                overwrite=overwrite or retry_failed,
                download_uri=download_uri,
                expected_size=expected_size,
            )
        except Exception as exc:
            LOGGER.warning("Download failed for %s: %s", file_name, exc)
            if retry_failed and destination.exists():
                destination.unlink(missing_ok=True)
            raise

        downloaded.append(destination)
        if entry is None:
            manifest.files[key] = FileEntry(
                path=key,
                source_url=download_uri or f"odp:{product_id}/{file_name}",
                status="pending",
            )
        else:
            entry.status = "pending"
            entry.error = None
            entry.source_url = download_uri or entry.source_url
        manifest.save(data_root / "manifest.json")

    if skipped:
        LOGGER.debug("Skipped %s already-ingested %s files", skipped, product_id)
    return downloaded


def _sync_weekly_dumps(
    *,
    data_root: Path,
    api_key: str,
    source: str = "both",
    weeks: int | None = None,
    output_format: str = "both",
    delete_raw: bool = True,
    max_fetch_errors: int = MAX_SYNC_FETCH_ERRORS,
) -> dict[str, int]:
    """Download and ingest weekly dumps until caught up or ``weeks`` is reached.

    ``source='both'`` interleaves grant and application weeks so both corpora
    fill from the start of the run.
    """
    products: list[str]
    if source == "both":
        products = [GRANT_FULLTEXT.odp_product_id, APPLICATION_FULLTEXT.odp_product_id]
    elif source == "grant":
        products = [GRANT_FULLTEXT.odp_product_id]
    else:
        products = [APPLICATION_FULLTEXT.odp_product_id]

    init_workspace(data_root)
    totals = {
        "weeks_ingested": 0,
        "documents_parsed": 0,
        "records_written": 0,
        "documents_failed": 0,
    }
    remaining = weeks
    exhausted: set[str] = set()
    empty_streak: dict[str, int] = {product_id: 0 for product_id in products}
    fetch_errors: dict[str, int] = {product_id: 0 for product_id in products}
    excluded_files: dict[str, set[str]] = {product_id: set() for product_id in products}

    while remaining is None or remaining > 0:
        progressed = False
        for product_id in products:
            if product_id in exhausted:
                continue
            if remaining is not None and remaining <= 0:
                break
            try:
                downloaded = fetch_from_odp(
                    product_id=product_id,
                    data_root=data_root,
                    api_key=api_key,
                    limit=1,
                    skip_existing=True,
                    exclude_filenames=excluded_files[product_id],
                )
            except Exception as exc:
                fetch_errors[product_id] += 1
                LOGGER.warning(
                    "Temporary failure fetching %s (%s/%s): %s",
                    product_id,
                    fetch_errors[product_id],
                    max_fetch_errors,
                    exc,
                )
                if fetch_errors[product_id] >= max_fetch_errors:
                    LOGGER.error("Stopping retries for product %s after repeated failures", product_id)
                    exhausted.add(product_id)
                else:
                    time.sleep(60)
                continue

            if not downloaded:
                empty_streak[product_id] = empty_streak.get(product_id, 0) + 1
                if empty_streak[product_id] >= 3:
                    LOGGER.info("Caught up on product %s.", product_id)
                    exhausted.add(product_id)
                else:
                    LOGGER.warning(
                        "No pending files for %s (streak %s/3); will retry later",
                        product_id,
                        empty_streak[product_id],
                    )
                    time.sleep(30)
                continue

            empty_streak[product_id] = 0
            fetch_errors[product_id] = 0
            source_path = downloaded[0]
            LOGGER.info("Ingesting weekly dump %s", source_path.name)
            try:
                stats = ingest_local_file(
                    source_path,
                    data_root=data_root,
                    output_format=output_format,
                )
            except Exception as exc:
                excluded_files[product_id].add(source_path.name)
                LOGGER.exception("Failed to ingest weekly dump %s: %s", source_path, exc)
                continue
            totals["weeks_ingested"] += 1
            totals["documents_parsed"] += stats.get("documents_parsed", 0)
            totals["records_written"] += stats.get("records_written", 0)
            totals["documents_failed"] += stats.get("documents_failed", 0)
            progressed = True

            if delete_raw and _is_archive_path(source_path) and source_path.exists():
                remove_raw_archive_after_ingest(source_path)

            if remaining is not None:
                remaining -= 1

            # Pace requests to reduce USPTO ODP rate-limit hits.
            time.sleep(5)

        if not progressed:
            if len(exhausted) == len(products):
                LOGGER.info("No remaining weekly dumps to fetch.")
                break
            LOGGER.warning("No progress this pass; cooling down 60s before retry")
            time.sleep(60)

    return totals


def sync_weekly_dumps(
    *,
    data_root: Path,
    api_key: str,
    source: str = "both",
    weeks: int | None = None,
    output_format: str = "both",
    delete_raw: bool = True,
    max_fetch_errors: int = MAX_SYNC_FETCH_ERRORS,
) -> dict[str, int]:
    """Run the resumable weekly sync under a process lock."""
    init_workspace(data_root)
    with _ingestion_lock(data_root):
        _recover_stale_manifest_runs(data_root)
        return _sync_weekly_dumps(
            data_root=data_root,
            api_key=api_key,
            source=source,
            weeks=weeks,
            output_format=output_format,
            delete_raw=delete_raw,
            max_fetch_errors=max_fetch_errors,
        )


def fetch_from_bdss(
    *,
    url: str,
    destination: Path,
    overwrite: bool = False,
) -> Path:
    """Download a file directly from the legacy BDSS URL."""
    return download_url(url, destination, overwrite=overwrite)


def print_status(data_root: Path = DEFAULT_DATA_ROOT) -> None:
    """Print ingestion manifest and database summary."""
    manifest = IngestManifest.load(data_root / "manifest.json")
    summary = manifest.summary()

    print("PatentPulse ingestion status")
    print("=" * 40)
    print(f"Files tracked:   {summary['files_total']}")
    print(f"Files complete:  {summary['files_complete']}")
    print(f"Files pending:   {summary['files_pending']}")
    print(f"Files running:   {summary['files_running']}")
    print(f"Files failed:    {summary['files_failed']}")
    print(f"Records parsed:  {summary['records_parsed']}")
    print(f"Records written: {summary['records_written']}")
    print(f"Parse failures:  {summary['records_failed']}")

    db_path = data_root / "processed" / "patents.db"
    if db_path.exists():
        import sqlite3

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA busy_timeout=5000")
        type_counts = dict(
            conn.execute(
                "SELECT document_type, COUNT(*) FROM patents GROUP BY document_type"
            ).fetchall()
        )
        grants = type_counts.get("grant", 0)
        apps = type_counts.get("application", 0)
        count = sum(type_counts.values())
        cpc_count = conn.execute("SELECT COUNT(*) FROM patent_cpc").fetchone()[0]
        latest = conn.execute(
            "SELECT publication_date FROM patents "
            "WHERE publication_date IS NOT NULL ORDER BY publication_date DESC LIMIT 1"
        ).fetchone()
        conn.close()
        print()
        print(f"Database:        {db_path}")
        print(f"Patent rows:     {count}")
        print(f"  grants:        {grants}")
        print(f"  applications:  {apps}")
        print(f"CPC rows:        {cpc_count}")
        if latest and latest[0]:
            print(f"Latest publication: {latest[0]}")

    if manifest.files:
        print()
        print("Recent files:")
        for entry in list(manifest.files.values())[-5:]:
            print(
                f"  [{entry.status}] {Path(entry.path).name} "
                f"parsed={entry.records_parsed} written={entry.records_written}"
            )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download USPTO bulk sources and ingest them into PatentPulse datasets.",
    )
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--verbose", "-v", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create data directories and seed bootstrap source.")

    run_parser = subparsers.add_parser("run", help="Ingest all files under data/raw.")
    run_parser.add_argument(
        "--format",
        choices=("sqlite", "jsonl", "both"),
        default="both",
    )
    run_parser.add_argument("--limit", type=int, default=None, help="Max patents per file.")
    run_parser.add_argument("--force", action="store_true", help="Re-ingest completed files.")

    fetch_parser = subparsers.add_parser("fetch", help="Download weekly bulk files from USPTO.")
    fetch_parser.add_argument(
        "--source",
        choices=("grant", "application"),
        default="grant",
    )
    fetch_parser.add_argument("--from-date", default=None, help="YYYY-MM-DD filter for ODP.")
    fetch_parser.add_argument("--to-date", default=None, help="YYYY-MM-DD filter for ODP.")
    fetch_parser.add_argument("--limit", type=int, default=1, help="Number of weekly files.")
    fetch_parser.add_argument("--api-key", default=None, help="USPTO ODP API key.")
    fetch_parser.add_argument(
        "--url",
        default=None,
        help="Direct BDSS/HTTP URL (bypasses ODP listing).",
    )
    fetch_parser.add_argument("--overwrite", action="store_true")

    sync_parser = subparsers.add_parser(
        "sync",
        help="Download each remaining weekly dump and ingest it.",
    )
    sync_parser.add_argument(
        "--source",
        choices=("grant", "application", "both"),
        default="both",
        help="Grant dumps, application dumps, or interleave both (default: both).",
    )
    sync_parser.add_argument(
        "--weeks",
        type=int,
        default=None,
        help="Max weekly files to process this run (default: all remaining).",
    )
    sync_parser.add_argument("--format", choices=("sqlite", "jsonl", "both"), default="both")
    sync_parser.add_argument(
        "--max-fetch-errors",
        type=int,
        default=MAX_SYNC_FETCH_ERRORS,
        help="Stop retrying one product after this many consecutive fetch failures.",
    )
    sync_parser.add_argument("--api-key", default=None, help="USPTO ODP API key.")
    sync_parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="Keep downloaded ZIP files after ingest (default: delete to save disk).",
    )

    subparsers.add_parser("status", help="Show manifest and database stats.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    try:
        if args.command == "init":
            init_workspace(args.data_root)
            print(f"Initialized workspace at {args.data_root.resolve()}")
            return 0

        if args.command == "status":
            print_status(args.data_root)
            return 0

        if args.command == "fetch":
            init_workspace(args.data_root)
            if args.url:
                filename = Path(args.url.split("/")[-1]).name
                kind = "grants" if "grant" in args.url or filename.startswith("ipg") else "applications"
                destination = args.data_root / "raw" / kind / filename
                with _ingestion_lock(args.data_root):
                    fetch_from_bdss(url=args.url, destination=destination, overwrite=args.overwrite)
                    manifest_path = args.data_root / "manifest.json"
                    manifest = IngestManifest.load(manifest_path)
                    key = str(destination.resolve())
                    entry = manifest.files.get(key) or FileEntry(path=key)
                    entry.status = "pending"
                    entry.source_url = args.url
                    entry.error = None
                    manifest.files[key] = entry
                    manifest.save(manifest_path)
                print(f"Downloaded {destination}")
                return 0

            api_key = resolve_api_key(args.api_key)
            if not api_key:
                LOGGER.error(
                    "USPTO ODP API key required. Set USPTO_API_KEY or pass --api-key. "
                    "Register at https://data.uspto.gov/apis/getting-started"
                )
                return 1

            product = (
                GRANT_FULLTEXT.odp_product_id
                if args.source == "grant"
                else APPLICATION_FULLTEXT.odp_product_id
            )
            with _ingestion_lock(args.data_root):
                paths = fetch_from_odp(
                    product_id=product,
                    data_root=args.data_root,
                    api_key=api_key,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    limit=args.limit,
                    overwrite=args.overwrite,
                )
            print(f"Downloaded {len(paths)} file(s) to {args.data_root / 'raw'}")
            return 0

        if args.command == "sync":
            api_key = resolve_api_key(args.api_key)
            if not api_key:
                LOGGER.error(
                    "USPTO ODP API key required. Set USPTO_API_KEY or pass --api-key. "
                    "Register at https://data.uspto.gov/apis/getting-started"
                )
                return 1
            totals = sync_weekly_dumps(
                data_root=args.data_root,
                api_key=api_key,
                source=args.source,
                weeks=args.weeks,
                output_format=args.format,
                delete_raw=not args.keep_raw,
                max_fetch_errors=args.max_fetch_errors,
            )
            print(
                "Sync complete — "
                f"weeks={totals['weeks_ingested']} "
                f"parsed={totals['documents_parsed']} "
                f"written={totals['records_written']} "
                f"failed={totals['documents_failed']}"
            )
            print_status(args.data_root)
            return 0

        if args.command == "run":
            init_workspace(args.data_root)
            totals = run_local_ingest(
                data_root=args.data_root,
                output_format=args.format,
                limit=args.limit,
                force=args.force,
            )
            print(
                "Ingestion complete — "
                f"files={totals['files_processed']} "
                f"parsed={totals['documents_parsed']} "
                f"written={totals['records_written']} "
                f"failed={totals['documents_failed']} "
                f"file_failures={totals.get('files_failed', 0)} "
                f"skipped={totals['files_skipped']}"
            )
            print_status(args.data_root)
            return 0

    except KeyboardInterrupt:
        LOGGER.warning("Interrupted.")
        return 130
    except Exception:
        LOGGER.exception("Ingestion failed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
