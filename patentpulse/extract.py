"""Field extraction from USPTO grant and application XML documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from lxml import etree

from patentpulse.clean import clean_patent_text, join_element_text

# Local tag names (namespace-agnostic).
TAG_BIBLIO_GRANT = "us-bibliographic-data-grant"
TAG_BIBLIO_APPLICATION = "us-bibliographic-data-application"
TAG_ABSTRACT = "abstract"
TAG_DESCRIPTION = "description"
TAG_CLAIMS = "claims"
TAG_INVENTION_TITLE = "invention-title"
TAG_PUBLICATION_REFERENCE = "publication-reference"
TAG_APPLICATION_REFERENCE = "application-reference"
TAG_DOCUMENT_ID = "document-id"
TAG_DOC_NUMBER = "doc-number"
TAG_DATE = "date"
TAG_CLASSIFICATIONS_CPC = "classifications-cpc"
TAG_MAIN_CPC = "main-cpc"
TAG_FURTHER_CPC = "further-cpc"
TAG_CLASSIFICATION_CPC = "classification-cpc"
TAG_CLASSIFICATION_CPC_TEXT = "classification-cpc-text"


@dataclass(slots=True)
class Inventor:
    inventor_name_last: str | None = None
    inventor_name_first: str | None = None
    inventor_city: str | None = None
    inventor_state: str | None = None
    inventor_country: str | None = None


@dataclass(slots=True)
class PatentRecord:
    """Normalized patent record aligned with HUPD-style Hugging Face fields."""

    patent_grant_id: str | None
    application_number: str | None
    publication_date: str | None
    invention_title: str | None
    abstract_text: str | None
    description_text: str | None
    claims_text: str | None
    primary_cpc_codes: list[str] = field(default_factory=list)
    further_cpc_codes: list[str] = field(default_factory=list)
    ipc_codes: list[str] = field(default_factory=list)
    document_type: str = "unknown"
    source_file: str | None = None
    kind_code: str | None = None
    country: str | None = None
    language: str | None = None
    filing_date: str | None = None
    date_produced: str | None = None
    application_type: str | None = None
    claim_count: int | None = None
    background: str | None = None
    summary: str | None = None
    examiner_name_last: str | None = None
    examiner_name_first: str | None = None
    assignee_names: list[str] = field(default_factory=list)
    inventor_list: list[Inventor] = field(default_factory=list)
    cited_patent_ids: list[str] = field(default_factory=list)
    npl_citations: list[str] = field(default_factory=list)
    related_application_numbers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        inventors = [asdict(item) for item in self.inventor_list]
        cpc_labels = list(dict.fromkeys([*self.primary_cpc_codes, *self.further_cpc_codes]))
        payload = {
            "patent_grant_id": self.patent_grant_id,
            "application_number": self.application_number,
            "publication_date": self.publication_date,
            "invention_title": self.invention_title,
            "abstract_text": self.abstract_text,
            "description_text": self.description_text,
            "claims_text": self.claims_text,
            "primary_cpc_codes": self.primary_cpc_codes,
            "further_cpc_codes": self.further_cpc_codes,
            "ipc_codes": self.ipc_codes,
            "document_type": self.document_type,
            "source_file": self.source_file,
            "kind_code": self.kind_code,
            "country": self.country,
            "language": self.language,
            "filing_date": self.filing_date,
            "date_produced": self.date_produced,
            "application_type": self.application_type,
            "claim_count": self.claim_count,
            "background": self.background,
            "summary": self.summary,
            "examiner_name_last": self.examiner_name_last,
            "examiner_name_first": self.examiner_name_first,
            "assignee_names": self.assignee_names,
            "inventor_list": inventors,
            "cited_patent_ids": self.cited_patent_ids,
            "npl_citations": self.npl_citations,
            "related_application_numbers": self.related_application_numbers,
            # HUPD / Hugging Face aliases
            "patent_number": self.patent_grant_id,
            "publication_number": self.patent_grant_id,
            "title": self.invention_title,
            "abstract": self.abstract_text,
            "claims": self.claims_text,
            "full_description": self.description_text,
            "date_published": self.publication_date,
            "patent_issue_date": self.publication_date if self.document_type == "grant" else None,
            "main_cpc_label": self.primary_cpc_codes[0] if self.primary_cpc_codes else None,
            "cpc_labels": cpc_labels,
            "main_ipcr_label": self.ipc_codes[0] if self.ipc_codes else None,
            "ipcr_labels": self.ipc_codes,
            "cited_patents": self.cited_patent_ids,
        }
        return payload


def _local_name(tag: str | None) -> str:
    if not isinstance(tag, str) or not tag:
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _find_child(parent: etree._Element, local_tag: str) -> etree._Element | None:
    for child in parent:
        if not isinstance(child.tag, str):
            continue
        if _local_name(child.tag) == local_tag:
            return child
    return None


def _find_children(parent: etree._Element, local_tag: str) -> list[etree._Element]:
    return [child for child in parent if _local_name(child.tag) == local_tag]


def _find_text(parent: etree._Element, local_tag: str) -> str | None:
    node = _find_child(parent, local_tag)
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value or None


def _format_uspto_date(raw: str | None) -> str | None:
    """Convert USPTO YYYYMMDD to ISO YYYY-MM-DD."""
    if not raw:
        return None
    digits = raw.strip()
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return digits


def _document_id_fields(
    reference: etree._Element,
) -> tuple[str | None, str | None, str | None, str | None]:
    doc_id = _find_child(reference, TAG_DOCUMENT_ID)
    if doc_id is None:
        return None, None, None, None
    number = _find_text(doc_id, TAG_DOC_NUMBER)
    date = _format_uspto_date(_find_text(doc_id, TAG_DATE))
    kind = _find_text(doc_id, "kind")
    country = _find_text(doc_id, "country")
    return number, date, kind, country


def _dedupe_codes(codes: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for code in codes:
        if code and code not in seen:
            seen.add(code)
            unique.append(code)
    return unique


def _collect_classification_codes(parent: etree._Element | None) -> list[str]:
    if parent is None:
        return []
    codes: list[str] = []
    for node in _find_children(parent, TAG_CLASSIFICATION_CPC):
        code = _compose_cpc_code(node)
        if code:
            codes.append(code)
    return _dedupe_codes(codes)


def _extract_cpc_codes(bibliographic: etree._Element) -> tuple[list[str], list[str]]:
    classifications = _find_child(bibliographic, TAG_CLASSIFICATIONS_CPC)
    if classifications is None:
        return [], []

    primary = _collect_classification_codes(_find_child(classifications, TAG_MAIN_CPC))
    further = _collect_classification_codes(_find_child(classifications, TAG_FURTHER_CPC))

    if not primary:
        fallback: list[str] = []
        for node in bibliographic.iter():
            if _local_name(node.tag) != TAG_CLASSIFICATION_CPC_TEXT or not node.text:
                continue
            fallback.append(node.text.strip().replace(" ", ""))
        primary = _dedupe_codes(fallback)

    return primary, [code for code in further if code not in primary]


def _extract_ipc_codes(bibliographic: etree._Element) -> list[str]:
    codes: list[str] = []
    container = _find_child(bibliographic, "classifications-ipcr")
    if container is None:
        return codes
    for node in _find_children(container, "classification-ipcr"):
        code = _compose_cpc_code(node)
        if code:
            codes.append(code)
    return _dedupe_codes(codes)


def _extract_people(bibliographic: etree._Element) -> tuple[list[Inventor], list[str]]:
    inventors: list[Inventor] = []
    assignees: list[str] = []
    seen_inventors: set[tuple[str | None, str | None]] = set()
    seen_assignees: set[str] = set()

    for node in bibliographic.iter():
        if not isinstance(node.tag, str):
            continue
        tag = _local_name(node.tag)
        book = _find_child(node, "addressbook")
        if book is None:
            book = node
        if tag in {"inventor", "applicant"}:
            last = _find_text(book, "last-name")
            first = _find_text(book, "first-name")
            key = (last, first)
            if (last or first) and key not in seen_inventors:
                seen_inventors.add(key)
                address = _find_child(book, "address")
                inventors.append(
                    Inventor(
                        inventor_name_last=last,
                        inventor_name_first=first,
                        inventor_city=_find_text(address, "city") if address is not None else None,
                        inventor_state=_find_text(address, "state") if address is not None else None,
                        inventor_country=_find_text(address, "country") if address is not None else None,
                    )
                )
        elif tag == "assignee":
            name = _find_text(book, "orgname") or " ".join(
                part for part in (_find_text(book, "first-name"), _find_text(book, "last-name")) if part
            )
            if name and name not in seen_assignees:
                seen_assignees.add(name)
                assignees.append(name)

    return inventors, assignees


def _extract_examiner(bibliographic: etree._Element) -> tuple[str | None, str | None]:
    examiners = _find_child(bibliographic, "examiners")
    if examiners is None:
        return None, None
    primary = _find_child(examiners, "primary-examiner")
    if primary is None:
        return None, None
    return _find_text(primary, "last-name"), _find_text(primary, "first-name")


def _format_cited_patent(
    country: str | None,
    number: str | None,
    kind: str | None,
) -> str | None:
    if not number:
        return None
    parts = [part for part in (country, number, kind) if part]
    return "-".join(parts)


def _extract_citations(bibliographic: etree._Element) -> tuple[list[str], list[str]]:
    cited: list[str] = []
    npl: list[str] = []
    for node in bibliographic.iter():
        if not isinstance(node.tag, str):
            continue
        tag = _local_name(node.tag)
        if tag == "patcit":
            number, _date, kind, country = _document_id_fields(node)
            formatted = _format_cited_patent(country, number, kind)
            if formatted:
                cited.append(formatted)
        elif tag in {"nplcit", "othercit"} and len(npl) < 40:
            text = join_element_text(node.itertext())
            if text:
                npl.append(text[:2000])
    return _dedupe_codes(cited), _dedupe_codes(npl)


def _extract_related_application_numbers(bibliographic: etree._Element) -> list[str]:
    container = _find_child(bibliographic, "us-related-documents")
    if container is None:
        return []
    numbers: list[str] = []
    for node in container.iter():
        if not isinstance(node.tag, str):
            continue
        if _local_name(node.tag) == TAG_DOC_NUMBER and node.text:
            numbers.append(node.text.strip())
    return _dedupe_codes(numbers)


def _split_description_sections(
    description_node: etree._Element | None,
) -> tuple[str | None, str | None]:
    if description_node is None:
        return None, None

    buckets: dict[str, list[str]] = {"background": [], "summary": [], "other": []}
    current = "other"
    for child in description_node:
        if not isinstance(child.tag, str):
            continue
        tag = _local_name(child.tag)
        text = join_element_text(child.itertext())
        if not text:
            continue
        heading = text.upper()
        if tag == "heading" and "BACKGROUND" in heading:
            current = "background"
            continue
        if tag == "heading" and heading.startswith("SUMMARY"):
            current = "summary"
            continue
        if tag == "heading" and "DETAILED DESCRIPTION" in heading:
            current = "other"
            continue
        if current in buckets:
            buckets[current].append(text)

    background = " ".join(buckets["background"]).strip() or None
    summary = " ".join(buckets["summary"]).strip() or None
    return background, summary


def _compose_cpc_code(node: etree._Element) -> str | None:
    """
    Build a CPC symbol from structured ``classification-cpc`` components.

    Falls back to ``classification-cpc-text`` when present.
    """
    text_value = _find_text(node, TAG_CLASSIFICATION_CPC_TEXT)
    if text_value:
        return text_value.replace(" ", "")

    section = _find_text(node, "section")
    cls = _find_text(node, "class")
    subclass = _find_text(node, "subclass")
    main_group = _find_text(node, "main-group")
    subgroup = _find_text(node, "subgroup")

    if not all((section, cls, subclass, main_group, subgroup)):
        return None

    return f"{section}{cls}{subclass}{main_group}/{subgroup}"


def _extract_primary_cpc_codes(bibliographic: etree._Element) -> list[str]:
    primary, _further = _extract_cpc_codes(bibliographic)
    return primary


def _extract_bibliographic(root: etree._Element) -> tuple[etree._Element | None, str]:
    root_name = _local_name(root.tag)
    if root_name == "us-patent-grant":
        biblio = _find_child(root, TAG_BIBLIO_GRANT)
        return biblio, "grant"
    if root_name == "us-patent-application":
        biblio = _find_child(root, TAG_BIBLIO_APPLICATION)
        return biblio, "application"
    return None, "unknown"


def _element_plain_text(node: etree._Element | None, *, strip_boilerplate: bool = True) -> str | None:
    if node is None:
        return None
    text = join_element_text(node.itertext())
    if strip_boilerplate:
        return text or None
    return clean_patent_text(" ".join(node.itertext()), strip_boilerplate=False) or None


def extract_patent_record(
    root: etree._Element,
    *,
    source_file: str | None = None,
) -> PatentRecord:
    """Extract normalized fields from a parsed USPTO document root."""
    bibliographic, document_type = _extract_bibliographic(root)

    patent_grant_id: str | None = None
    application_number: str | None = None
    publication_date: str | None = None
    invention_title: str | None = None
    primary_cpc_codes: list[str] = []
    further_cpc_codes: list[str] = []
    ipc_codes: list[str] = []
    kind_code: str | None = None
    country: str | None = root.get("country")
    language: str | None = root.get("lang")
    filing_date: str | None = None
    date_produced: str | None = _format_uspto_date(root.get("date-produced"))
    application_type: str | None = None
    inventors: list[Inventor] = []
    assignees: list[str] = []
    examiner_last: str | None = None
    examiner_first: str | None = None
    cited_patent_ids: list[str] = []
    npl_citations: list[str] = []
    related_application_numbers: list[str] = []

    if bibliographic is not None:
        invention_title = clean_patent_text(
            _find_text(bibliographic, TAG_INVENTION_TITLE) or "",
            strip_boilerplate=False,
        ) or None

        for reference in _find_children(bibliographic, TAG_PUBLICATION_REFERENCE):
            number, date, kind, pub_country = _document_id_fields(reference)
            if number:
                patent_grant_id = number
            if date:
                publication_date = date
            if kind:
                kind_code = kind
            if pub_country:
                country = pub_country

        for reference in _find_children(bibliographic, TAG_APPLICATION_REFERENCE):
            number, app_date, _kind, _country = _document_id_fields(reference)
            if number:
                application_number = number
            if app_date:
                filing_date = app_date
            application_type = reference.get("appl-type") or application_type

        primary_cpc_codes, further_cpc_codes = _extract_cpc_codes(bibliographic)
        ipc_codes = _extract_ipc_codes(bibliographic)
        inventors, assignees = _extract_people(bibliographic)
        examiner_last, examiner_first = _extract_examiner(bibliographic)
        cited_patent_ids, npl_citations = _extract_citations(bibliographic)
        related_application_numbers = _extract_related_application_numbers(bibliographic)

    abstract_node = _find_child(root, TAG_ABSTRACT)
    description_node = _find_child(root, TAG_DESCRIPTION)
    claims_node = _find_child(root, TAG_CLAIMS)
    background, summary = _split_description_sections(description_node)
    claim_count = len(_find_children(claims_node, "claim")) if claims_node is not None else None

    return PatentRecord(
        patent_grant_id=patent_grant_id,
        application_number=application_number,
        publication_date=publication_date,
        invention_title=invention_title,
        abstract_text=_element_plain_text(abstract_node, strip_boilerplate=False),
        description_text=_element_plain_text(description_node, strip_boilerplate=True),
        claims_text=_element_plain_text(claims_node, strip_boilerplate=False),
        primary_cpc_codes=primary_cpc_codes,
        further_cpc_codes=further_cpc_codes,
        ipc_codes=ipc_codes,
        document_type=document_type,
        source_file=source_file,
        kind_code=kind_code,
        country=country,
        language=language,
        filing_date=filing_date,
        date_produced=date_produced,
        application_type=application_type,
        claim_count=claim_count or None,
        background=background,
        summary=summary,
        examiner_name_last=examiner_last,
        examiner_name_first=examiner_first,
        assignee_names=assignees,
        inventor_list=inventors,
        cited_patent_ids=cited_patent_ids,
        npl_citations=npl_citations,
        related_application_numbers=related_application_numbers,
    )


def extract_patent_from_xml(
    xml_payload: str | bytes,
    *,
    source_file: str | None = None,
    use_iterparse: bool = True,
) -> PatentRecord:
    """
    Parse one complete XML document and extract a :class:`PatentRecord`.

    When ``use_iterparse`` is True, the parser walks the tree incrementally and
    clears nodes as they are consumed to minimize peak memory per document.
    """
    if use_iterparse:
        return _extract_with_iterparse(xml_payload, source_file=source_file)
    from patentpulse.stream import parse_document_root

    root = parse_document_root(xml_payload)
    try:
        return extract_patent_record(root, source_file=source_file)
    finally:
        root.clear()


def _extract_with_iterparse(
    xml_payload: str | bytes,
    *,
    source_file: str | None,
) -> PatentRecord:
    """
    Parse one document with iterparse and extract at the root ``end`` event.

    When the root closes, all descendant nodes are available; we extract once
    and then clear the tree to release memory before the next document.
    """
    import io

    from patentpulse.stream import DOCUMENT_ROOT_TAGS

    if isinstance(xml_payload, str):
        xml_payload = xml_payload.encode("utf-8")

    context = etree.iterparse(
        io.BytesIO(xml_payload),
        events=("end",),
        huge_tree=True,
        recover=True,
    )

    root: etree._Element | None = None
    for _event, element in context:
        if _local_name(element.tag) in DOCUMENT_ROOT_TAGS:
            root = element
            break

    if root is None:
        return PatentRecord(
            patent_grant_id=None,
            application_number=None,
            publication_date=None,
            invention_title=None,
            abstract_text=None,
            description_text=None,
            claims_text=None,
            document_type="unknown",
            source_file=source_file,
        )

    try:
        return extract_patent_record(root, source_file=source_file)
    finally:
        root.clear()
        while root.getprevious() is not None:
            del root.getparent()[0]
