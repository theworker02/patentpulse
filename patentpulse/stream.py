"""Memory-bounded streaming readers for concatenated USPTO bulk XML files."""

from __future__ import annotations

import gzip
import io
import re
import tarfile
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, TextIO

from lxml import etree

# USPTO weekly bulk files concatenate thousands of standalone XML documents.
_XML_DECL_RE = re.compile(r"^<\?xml\b", re.MULTILINE)
_GRANT_CLOSE = "</us-patent-grant>"
_APPLICATION_CLOSE = "</us-patent-application>"
_CLOSE_TAGS = (_GRANT_CLOSE, _APPLICATION_CLOSE)

# Root tags emitted by Red Book grant and application full-text dumps.
DOCUMENT_ROOT_TAGS = frozenset({"us-patent-grant", "us-patent-application"})


def _detect_close_tag(buffer: str) -> str | None:
    for tag in _CLOSE_TAGS:
        if tag in buffer:
            return tag
    return None


def iter_concatenated_documents(
    text_stream: TextIO,
    *,
    max_document_bytes: int = 128 * 1024 * 1024,
) -> Iterator[str]:
    """
    Yield one complete USPTO XML document at a time from a concatenated bulk file.

    Bulk weekly files are not valid single XML trees; they are many documents
    glued together at ``<?xml`` boundaries. Sequence-listing and other companion
    documents are yielded as well; callers should skip unknown roots.
    """
    chunk: list[str] = []
    current_size = 0
    skipping = False

    def _flush() -> str | None:
        nonlocal current_size, skipping
        skipping = False
        if not chunk:
            return None
        document = "".join(chunk)
        chunk.clear()
        current_size = 0
        return document

    for line in text_stream:
        if _XML_DECL_RE.match(line):
            finished = _flush()
            if finished is not None:
                yield finished

        if skipping:
            continue

        line_size = len(line.encode("utf-8", errors="replace"))
        if current_size + line_size > max_document_bytes:
            chunk.clear()
            current_size = 0
            skipping = True
            continue

        chunk.append(line)
        current_size += line_size

    finished = _flush()
    if finished is not None:
        yield finished


def _xml_member_names(names: list[str]) -> list[str]:
    return sorted(name for name in names if name.lower().endswith(".xml"))


def _is_tar_path(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".tar") or name.endswith(".tar.gz") or name.endswith(".tgz")


def open_bulk_text(
    path: Path,
) -> tuple[TextIO, zipfile.ZipFile | tarfile.TarFile | gzip.GzipFile | None]:
    """Open plain XML, ZIP, TAR/TAR.GZ, or GZIP-wrapped XML text."""
    if path.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(path)
        members = _xml_member_names(zf.namelist())
        if not members:
            zf.close()
            raise FileNotFoundError(f"No .xml member found in ZIP: {path}")
        raw = zf.open(members[0])
        return io.TextIOWrapper(raw, encoding="utf-8", errors="replace"), zf

    if _is_tar_path(path):
        archive = tarfile.open(path, mode="r:*")
        members = sorted(
            member for member in archive.getmembers()
            if member.isfile() and member.name.lower().endswith(".xml")
        )
        if not members:
            archive.close()
            raise FileNotFoundError(f"No .xml member found in TAR: {path}")
        raw = archive.extractfile(members[0])
        if raw is None:
            archive.close()
            raise FileNotFoundError(f"Unable to read XML member in TAR: {path}")
        return io.TextIOWrapper(raw, encoding="utf-8", errors="replace"), archive

    if path.suffix.lower() == ".gz":
        gzip_handle = gzip.open(path, mode="rb")
        return io.TextIOWrapper(gzip_handle, encoding="utf-8", errors="replace"), gzip_handle

    return path.open("r", encoding="utf-8", errors="replace"), None


def iterparse_document(xml_payload: str | bytes) -> Iterator[tuple[str, etree._Element]]:
    """
    iterparse wrapper for a single patent document buffer.

    Yields ``(event, element)`` pairs and clears processed nodes to bound memory.
    """
    if isinstance(xml_payload, str):
        xml_payload = xml_payload.encode("utf-8")

    context = etree.iterparse(
        io.BytesIO(xml_payload),
        events=("end",),
        huge_tree=True,
        recover=True,
        remove_blank_text=False,
    )
    for event, element in context:
        yield event, element
        if element.getparent() is not None:
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]


def parse_document_root(xml_payload: str | bytes) -> etree._Element:
    """Parse one complete document and return its root element."""
    if isinstance(xml_payload, str):
        xml_payload = xml_payload.encode("utf-8")
    return etree.fromstring(xml_payload, parser=etree.XMLParser(huge_tree=True, recover=True))


def open_binary_source(
    path: Path,
) -> tuple[BinaryIO, zipfile.ZipFile | tarfile.TarFile | gzip.GzipFile | None]:
    """Open raw bytes from plain XML, ZIP, TAR/TAR.GZ, or GZIP input."""
    if path.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(path)
        members = _xml_member_names(zf.namelist())
        if not members:
            zf.close()
            raise FileNotFoundError(f"No .xml member found in ZIP: {path}")
        return zf.open(members[0]), zf

    if _is_tar_path(path):
        archive = tarfile.open(path, mode="r:*")
        members = sorted(
            member for member in archive.getmembers()
            if member.isfile() and member.name.lower().endswith(".xml")
        )
        if not members:
            archive.close()
            raise FileNotFoundError(f"No .xml member found in TAR: {path}")
        raw = archive.extractfile(members[0])
        if raw is None:
            archive.close()
            raise FileNotFoundError(f"Unable to read XML member in TAR: {path}")
        return raw, archive

    if path.suffix.lower() == ".gz":
        gzip_handle = gzip.open(path, mode="rb")
        return gzip_handle, gzip_handle

    return path.open("rb"), None
