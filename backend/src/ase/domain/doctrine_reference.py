"""Pinned public methodology references, not evidence or doctrinal accreditation.

Hashes cover exact UTF-8 excerpts and canonical registry metadata. They detect
local drift; they do not authenticate a publisher or recheck a website offline.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

OFFICIAL_REFERENCE_HOSTS = frozenset(
    {"www.gov.uk", "assets.publishing.service.gov.uk", "quicksearch.dla.mil"}
)


def _official_url(value: str) -> None:
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or url.hostname not in OFFICIAL_REFERENCE_HOSTS
        or url.username is not None
        or url.password is not None
        or url.port is not None
        or any(ord(char) < 33 for char in value)
    ):
        raise ValueError("Doctrine references require an explicit official HTTPS source.")


@dataclass(frozen=True, slots=True)
class DoctrineExcerpt:
    text: str
    source_url: str
    locator: str
    reuse_basis: str
    sha256: str

    def __post_init__(self) -> None:
        _official_url(self.source_url)
        if not self.text.strip() or len(self.text.split()) > 25 or len(self.text) > 500:
            raise ValueError("Only short, attributed public excerpts belong in the registry.")
        if not self.locator.strip() or not self.reuse_basis.strip():
            raise ValueError("An excerpt needs its source location and reuse basis.")
        if self.sha256 != hashlib.sha256(self.text.encode("utf-8")).hexdigest():
            raise ValueError("The pinned doctrine excerpt hash does not match its text.")


@dataclass(frozen=True, slots=True)
class DoctrineReference:
    identifier: str
    title: str
    publisher: str
    url: str
    edition: str
    version: str | None
    publication_date: str
    date_basis: Literal["publication", "edition_month", "promulgation"]
    retrieved_on: date
    verification_scope: Literal["public_guidance", "publication_metadata", "catalogue_metadata"]
    catalogue_publisher: str
    catalogue_published_on: date | None
    catalogue_updated_on: date | None
    publication_url: str | None
    summary: str
    access_note: str
    excerpt: DoctrineExcerpt

    def __post_init__(self) -> None:
        _official_url(self.url)
        if self.publication_url is not None:
            _official_url(self.publication_url)
        for value in (
            self.identifier,
            self.title,
            self.publisher,
            self.edition,
            self.summary,
            self.catalogue_publisher,
            self.access_note,
        ):
            if not value.strip() or len(value) > 1200:
                raise ValueError("Reference metadata must be explicit and bounded.")
        if self.version is not None and not self.version.strip():
            raise ValueError("An unverified publication version must remain absent.")
        if self.date_basis not in ("publication", "edition_month", "promulgation"):
            raise ValueError("The publication date needs an explicit basis.")
        pattern = r"\d{4}-\d{2}" if self.date_basis == "edition_month" else r"\d{4}-\d{2}-\d{2}"
        if re.fullmatch(pattern, self.publication_date) is None:
            raise ValueError("The pinned publication date must retain its verified precision.")
        earliest = date.fromisoformat(
            self.publication_date + "-01"
            if self.date_basis == "edition_month"
            else self.publication_date
        )
        if type(self.retrieved_on) is not date or earliest > self.retrieved_on:
            raise ValueError("Reference retrieval cannot predate its publication.")
        for catalogue_date in (self.catalogue_published_on, self.catalogue_updated_on):
            if catalogue_date is not None and (
                type(catalogue_date) is not date or catalogue_date > self.retrieved_on
            ):
                raise ValueError("Catalogue dates cannot postdate the recorded retrieval.")
        if self.verification_scope not in (
            "public_guidance",
            "publication_metadata",
            "catalogue_metadata",
        ):
            raise ValueError("Reference verification scope must be explicit.")
        if self.verification_scope == "catalogue_metadata" and self.publication_url is not None:
            raise ValueError("Catalogue-only verification cannot imply a verified publication URL.")


def reference_pack_sha256(references: tuple[DoctrineReference, ...]) -> str:
    """Hash exact ordered metadata; whitespace in excerpts is deliberately significant."""
    encoded = json.dumps(
        [asdict(reference) for reference in references],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=date.isoformat,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_reference_pack(references: tuple[DoctrineReference, ...], expected_hash: str) -> None:
    if (
        type(references) is not tuple
        or not 1 <= len(references) <= 16
        or any(not isinstance(reference, DoctrineReference) for reference in references)
        or len({reference.identifier for reference in references}) != len(references)
        or reference_pack_sha256(references) != expected_hash
    ):
        raise ValueError("The pinned public doctrine reference pack has changed.")
