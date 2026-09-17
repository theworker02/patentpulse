"""Text normalization and legal boilerplate stripping for USPTO patent prose."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Iterable

# XML processing-instruction artifacts sometimes leak into itertext output.
_PI_ARTIFACT_RE = re.compile(r"<\?[^?>]+\?>", re.IGNORECASE)

# Collapse runs of whitespace while preserving single newlines between paragraphs.
_MULTI_SPACE_RE = re.compile(r"[^\S\n]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Known legal front-matter headings (removed with their immediate prose).
_BOILERPLATE_HEADERS: tuple[str, ...] = (
    "CROSS-REFERENCE TO RELATED APPLICATIONS",
    "CROSS-REFERENCE TO RELATED APPLICATION",
    "STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT",
    "STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH",
    "REFERENCE TO SEQUENCE LISTING, A TABLE, OR A COMPUTER PROGRAM",
    "REFERENCE TO SEQUENCE LISTING",
    "GOVERNMENT INTEREST",
    "COPYRIGHT NOTICE",
)

# Technical section headings preserved as structural anchors.
_SECTION_HEADINGS: tuple[str, ...] = (
    "TECHNICAL FIELD",
    "FIELD OF THE INVENTION",
    "FIELD OF INVENTION",
    "BACKGROUND OF THE INVENTION",
    "BACKGROUND",
    "SUMMARY OF THE INVENTION",
    "SUMMARY",
    "BRIEF DESCRIPTION OF THE DRAWINGS",
    "BRIEF DESCRIPTION OF DRAWINGS",
    "DETAILED DESCRIPTION OF THE PREFERRED EMBODIMENTS",
    "DETAILED DESCRIPTION",
)

# Standalone one-line legal disclaimers.
_LEGAL_LINE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\s*The present application claims priority to .+$",
        r"^\s*This application is a continuation(?:[- ]in[- ]part)? of .+$",
        r"^\s*This patent application is related to .+$",
    )
)


def normalize_whitespace(text: str) -> str:
    """Collapse irregular whitespace while keeping paragraph breaks."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def decode_xml_entities(text: str) -> str:
    """Resolve HTML/XML entities without destroying technical notation."""
    if not text:
        return ""
    text = html.unescape(text)
    # Some dumps double-encode entities; one more pass is usually enough.
    text = html.unescape(text)
    return text


def _section_pattern() -> re.Pattern[str]:
    escaped = "|".join(re.escape(section) for section in _SECTION_HEADINGS)
    return re.compile(rf"\b(?:{escaped})\b", re.IGNORECASE)


def strip_legal_boilerplate(text: str) -> str:
    """Remove repetitive legal header blocks; keep section headings and body."""
    if not text:
        return ""

    flattened = normalize_whitespace(text.replace("\n", " "))
    section_re = _section_pattern()
    cleaned = flattened

    for header in _BOILERPLATE_HEADERS:
        header_re = re.compile(rf"{re.escape(header)}\b\s*", re.IGNORECASE)
        match = header_re.search(cleaned)
        if not match:
            continue

        tail = cleaned[match.end() :]
        next_section = section_re.search(tail)
        if next_section:
            cleaned = cleaned[: match.start()] + tail[next_section.start() :]
        else:
            cleaned = cleaned[: match.start()]

    lines: list[str] = []
    for line in cleaned.split("\n"):
        if any(pattern.match(line) for pattern in _LEGAL_LINE_PATTERNS):
            continue
        lines.append(line)

    return normalize_whitespace(" ".join(lines))


def strip_markup_artifacts(text: str) -> str:
    """Remove PI remnants and stray markup fragments from flattened XML text."""
    if not text:
        return ""
    text = _PI_ARTIFACT_RE.sub("", text)
    text = text.replace("<", " ").replace(">", " ")
    return normalize_whitespace(text)


def clean_patent_text(text: str, *, strip_boilerplate: bool = True) -> str:
    """Full cleaning pipeline for abstract, description, and claims."""
    if not text:
        return ""

    text = decode_xml_entities(text)
    text = strip_markup_artifacts(text)
    if strip_boilerplate:
        text = strip_legal_boilerplate(text)
    return normalize_whitespace(text)


def join_element_text(chunks: Iterable[str]) -> str:
    """Join itertext fragments with sensible spacing."""
    parts = [chunk.strip() for chunk in chunks if chunk and chunk.strip()]
    return clean_patent_text(" ".join(parts))
