"""USPTO bulk data source catalog and URL builders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceKind(str, Enum):
    GRANT_FULLTEXT = "grant_fulltext"
    APPLICATION_FULLTEXT = "application_fulltext"


@dataclass(frozen=True, slots=True)
class BulkSource:
    """Describes a USPTO bulk data product."""

    kind: SourceKind
    product_id: str
    label: str
    bdss_path_template: str
    odp_product_id: str


GRANT_FULLTEXT = BulkSource(
    kind=SourceKind.GRANT_FULLTEXT,
    product_id="PTGRXML",
    label="Patent Grant Full Text (XML, no images)",
    bdss_path_template="data/patent/grant/redbook/fulltext/{year}/{filename}",
    odp_product_id="PTGRXML",
)

APPLICATION_FULLTEXT = BulkSource(
    kind=SourceKind.APPLICATION_FULLTEXT,
    product_id="APPXML",
    label="Patent Application Full Text (XML, no images)",
    bdss_path_template="data/patent/application/redbook/fulltext/{year}/{filename}",
    odp_product_id="APPXML",
)

DEFAULT_SOURCES: dict[SourceKind, BulkSource] = {
    SourceKind.GRANT_FULLTEXT: GRANT_FULLTEXT,
    SourceKind.APPLICATION_FULLTEXT: APPLICATION_FULLTEXT,
}

BDSS_BASE_URL = "https://bulkdata.uspto.gov"
ODP_API_BASE_URL = "https://api.uspto.gov"


def bdss_file_url(source: BulkSource, *, year: int, filename: str) -> str:
    """Build a legacy Bulk Data Storage System download URL."""
    path = source.bdss_path_template.format(year=year, filename=filename)
    return f"{BDSS_BASE_URL}/{path}"


def grant_zip_name(*, year: int, month: int, day: int) -> str:
    """Return the canonical weekly grant ZIP name (``ipgYYMMDD.zip``)."""
    return f"ipg{year % 100:02d}{month:02d}{day:02d}.zip"


def application_zip_name(*, year: int, month: int, day: int) -> str:
    """Return the canonical weekly application ZIP name (``ipaYYMMDD.zip``)."""
    return f"ipa{year % 100:02d}{month:02d}{day:02d}.zip"
