"""Resilient download helpers for USPTO bulk source files."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from patentpulse.sources import ODP_API_BASE_URL

LOGGER = logging.getLogger("patentpulse.download")

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


CHUNK_SIZE = 1024 * 1024
RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})
MAX_DOWNLOAD_RETRIES = 8
BASE_RETRY_SECONDS = 30


def download_url(
    url: str,
    destination: Path,
    *,
    api_key: str | None = None,
    overwrite: bool = False,
    expected_size: int | None = None,
) -> Path:
    """Stream-download a remote file atomically with size validation and retries."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        if expected_size is None or destination.stat().st_size == expected_size:
            LOGGER.info("Already downloaded: %s", destination)
            return destination
        LOGGER.warning(
            "Existing download has size %s, expected %s; replacing %s",
            destination.stat().st_size,
            expected_size,
            destination,
        )
        destination.unlink()

    headers = {"User-Agent": "patentpulse/0.1 (+https://github.com/theworker02/patentpulse)"}
    if api_key:
        headers["X-API-KEY"] = api_key

    LOGGER.info("Downloading %s -> %s", url, destination)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")

    for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
        temporary.unlink(missing_ok=True)
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=600) as response, temporary.open("wb") as out:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())

            if expected_size is not None and temporary.stat().st_size != expected_size:
                raise RuntimeError(
                    f"incomplete download: got {temporary.stat().st_size} bytes, "
                    f"expected {expected_size}"
                )
            os.replace(temporary, destination)
            return destination
        except urllib.error.HTTPError as exc:
            temporary.unlink(missing_ok=True)
            if exc.code in RETRYABLE_HTTP_CODES and attempt < MAX_DOWNLOAD_RETRIES:
                wait = BASE_RETRY_SECONDS * (2 ** (attempt - 1))
                LOGGER.warning(
                    "HTTP %s on attempt %s/%s; retrying in %ss: %s",
                    exc.code,
                    attempt,
                    MAX_DOWNLOAD_RETRIES,
                    wait,
                    url,
                )
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {exc.code} downloading {url}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            temporary.unlink(missing_ok=True)
            if attempt < MAX_DOWNLOAD_RETRIES:
                wait = BASE_RETRY_SECONDS * (2 ** (attempt - 1))
                LOGGER.warning(
                    "Network error on attempt %s/%s; retrying in %ss: %s",
                    attempt,
                    MAX_DOWNLOAD_RETRIES,
                    wait,
                    exc.reason,
                )
                time.sleep(wait)
                continue
            raise RuntimeError(f"Network error downloading {url}: {exc.reason}") from exc
        except RuntimeError as exc:
            temporary.unlink(missing_ok=True)
            if attempt < MAX_DOWNLOAD_RETRIES:
                wait = BASE_RETRY_SECONDS * (2 ** (attempt - 1))
                LOGGER.warning(
                    "Download validation failed on attempt %s/%s; retrying in %ss: %s",
                    attempt,
                    MAX_DOWNLOAD_RETRIES,
                    wait,
                    exc,
                )
                time.sleep(wait)
                continue
            raise

    temporary.unlink(missing_ok=True)
    raise RuntimeError(f"Failed to download {url} after {MAX_DOWNLOAD_RETRIES} attempts.")


def _odp_get(path: str, *, api_key: str, query: dict[str, str] | None = None) -> Any:
    query_string = ""
    if query:
        query_string = "?" + urllib.parse.urlencode(query)
    url = f"{ODP_API_BASE_URL}/{path.lstrip('/')}{query_string}"
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
        "User-Agent": "patentpulse/0.1",
    }

    for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_HTTP_CODES and attempt < MAX_DOWNLOAD_RETRIES:
                wait = BASE_RETRY_SECONDS * (2 ** (attempt - 1))
                LOGGER.warning(
                    "HTTP %s listing %s (attempt %s/%s); retrying in %ss",
                    exc.code,
                    url,
                    attempt,
                    MAX_DOWNLOAD_RETRIES,
                    wait,
                )
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as exc:
            if attempt < MAX_DOWNLOAD_RETRIES:
                wait = BASE_RETRY_SECONDS * (2 ** (attempt - 1))
                LOGGER.warning(
                    "Network error listing %s (attempt %s/%s); retrying in %ss: %s",
                    url,
                    attempt,
                    MAX_DOWNLOAD_RETRIES,
                    wait,
                    exc.reason,
                )
                time.sleep(wait)
                continue
            raise

    raise RuntimeError(f"Failed to query ODP endpoint after {MAX_DOWNLOAD_RETRIES} attempts: {url}")


def _extract_file_bag(payload: Any) -> list[dict[str, Any]]:
    """Normalize USPTO ODP product payloads into a list of file records."""
    products = payload.get("bulkDataProductBag") if isinstance(payload, dict) else None
    if products:
        payload = products[0]
    product = payload.get("product", payload) if isinstance(payload, dict) else {}
    bag = product.get("productFileBag") or product.get("files") or product.get("fileData") or []
    if isinstance(bag, dict):
        bag = bag.get("fileDataBag", [])
    return [item for item in (bag or []) if isinstance(item, dict)]


def list_odp_product_files(
    product_id: str,
    *,
    api_key: str,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int | None = 20,
) -> list[dict[str, Any]]:
    """List downloadable files for a USPTO ODP bulk product."""
    query: dict[str, str] = {"includeFiles": "true"}
    if from_date:
        query["fileDataFromDate"] = from_date
    if to_date:
        query["fileDataToDate"] = to_date

    files: list[dict[str, Any]] = []
    for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
        payload = _odp_get(f"api/v1/datasets/products/{product_id}", api_key=api_key, query=query)
        files = _extract_file_bag(payload)
        if files:
            break
        if attempt < MAX_DOWNLOAD_RETRIES:
            wait = BASE_RETRY_SECONDS * (2 ** (attempt - 1))
            LOGGER.warning(
                "Empty file list for %s (attempt %s/%s); retrying in %ss",
                product_id,
                attempt,
                MAX_DOWNLOAD_RETRIES,
                wait,
            )
            time.sleep(wait)

    files.sort(key=lambda item: item.get("fileDataFromDate") or item.get("fileName") or "", reverse=True)
    if limit is None:
        return files
    return files[:limit]


def download_odp_file(
    product_id: str,
    file_name: str,
    destination: Path,
    *,
    api_key: str,
    overwrite: bool = False,
    download_uri: str | None = None,
    expected_size: int | None = None,
) -> Path:
    """Download one ODP bulk file by product id and file name."""
    url = download_uri or f"{ODP_API_BASE_URL}/api/v1/datasets/products/files/{product_id}/{file_name}"
    return download_url(
        url,
        destination,
        api_key=api_key,
        overwrite=overwrite,
        expected_size=expected_size,
    )


def resolve_api_key(explicit: str | None = None) -> str | None:
    """Return an ODP API key from CLI flag or environment."""
    return explicit or os.environ.get("USPTO_API_KEY") or os.environ.get("PATENTPULSE_USPTO_API_KEY")
