"""Inert bounded filing text, with locators into a separately hashed original."""

import hashlib
import re
from dataclasses import replace
from datetime import UTC, datetime
from html.parser import HTMLParser

from ase.adapters.research_records.records import record_event
from ase.application.ports.research_inputs import InputExtraction
from ase.domain.events import Category, Reliability, content_hash
from ase.domain.sec_filing_time import filing_source_date
from ase.domain.sec_filings import SecFiling

MAX_TEXT = 112000
MAX_NODES = 100000


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: list[str] = []
        self.nodes = 0
        self.size = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._token()
        values = dict(attrs)
        style = (values.get("style") or "").replace(" ", "").lower()
        if (
            self.hidden
            or tag in {"script", "style", "head", "iframe", "object", "ix:hidden"}
            or ("hidden" in values or "display:none" in style or "visibility:hidden" in style)
        ):
            if tag not in {"br", "img", "meta", "link", "input", "hr"}:
                self.hidden.append(tag)
                if len(self.hidden) > 128:
                    raise ValueError("Filing markup exceeds the hidden nesting limit")
        elif tag in {"p", "div", "tr", "td", "th", "br", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        self._token()
        if self.hidden and tag in self.hidden:
            index = len(self.hidden) - 1 - self.hidden[::-1].index(tag)
            del self.hidden[index:]

    def _token(self) -> None:
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise ValueError("Filing markup exceeds the parser complexity limit")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.size += len(data)
            if self.size > 2_000_000:
                raise ValueError("Filing text exceeds the extraction processing bound")
            self.parts.append(data)


def document_url(filing: SecFiling) -> str:
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(filing.cik)}/"
        f"{filing.accession.replace('-', '')}/{filing.primary_document}"
    )


def extract(data: bytes, filing: SecFiling, captured: datetime) -> InputExtraction:
    if not data or len(data) > 4 * 1024 * 1024 or b"\x00" in data:
        raise ValueError("Filing bytes are empty, binary or exceed the 4 MiB limit")
    # SEC documents include older declared Windows-1252 text as well as UTF-8.
    try:
        decoded = data.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        decoded, encoding = data.decode("cp1252"), "windows-1252"
    if data.startswith((b"%PDF-", b"PK\x03\x04", b"\x89PNG", b"GIF8", b"\xff\xd8")) or any(
        ord(char) < 32 and char not in "\r\n\t\f" for char in decoded
    ):
        raise ValueError("The selected primary document is not supported HTML or text")
    media_type = "text/plain" if filing.primary_document.lower().endswith(".txt") else "text/html"
    if media_type == "text/html":
        parser = _Text()
        parser.feed(decoded)
        parser.close()
        decoded = "".join(parser.parts)
    text = re.sub(r"\s+", " ", decoded).strip()
    if any(
        marker in text.lower()
        for marker in (
            "your request originates from an undeclared automated tool",
            "request rate threshold exceeded",
            "sec.gov | access denied",
        )
    ):
        raise ValueError("SEC returned an access-policy response instead of filing content")
    if not text:
        raise ValueError("The selected filing has no extractable visible text")
    truncated = len(text) > MAX_TEXT
    text = text[:MAX_TEXT]
    digest = hashlib.sha256(data).hexdigest()
    normalised_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    limitations = (
        "Issuer-filed content is not independently verified by the SEC or this application.",
        "Locators identify character offsets in ase-sec-text-v1 extracted text, not "
        "HTML byte offsets.",
        "The filing date is publication metadata with day precision, not the period "
        "described in the filing.",
        "Original bytes are held transiently for download until selection expiry; "
        "durable retention is separate.",
        "HTML scripts, styles and hidden elements are omitted; tables lose visual layout.",
    ) + (("Extracted text was truncated at 112,000 characters.",) if truncated else ())
    events = []
    for start in range(0, len(text), 1400):
        end = min(start + 1400, len(text))
        events.append(
            record_event(
                "research_import",
                f"sec:{digest}:{start}",
                f"{filing.company_name}: {filing.form} [{start}:{end}]"[:300],
                text[start:end],
                document_url(filing),
                captured,
                category=Category.ECONOMIC,
                published=datetime.combine(filing.filing_date, datetime.min.time(), tzinfo=UTC),
                attributes={
                    "original_sha256": digest,
                    "filename": filing.primary_document,
                    "media_type": media_type,
                    "original_byte_count": len(data),
                    "cik": filing.cik,
                    "accession": filing.accession,
                    "filing_date": filing.filing_date.isoformat(),
                    "date_precision": "day",
                    "record_kind": "sec_filing_content",
                    "upstream_source": "sec_edgar",
                    "parser_method": "ase-sec-text-v1",
                    "text_encoding": encoding,
                    "text_start": start,
                    "text_end": end,
                    "extracted_sha256": normalised_digest,
                    "text_truncated": truncated,
                },
            )
        )
    events = [
        replace(
            event,
            summary=text[index * 1400 : (index + 1) * 1400],
            content_hash=content_hash(event.title, text[index * 1400 : (index + 1) * 1400]),
            reliability=Reliability.F,
            published_at=None,
            source_dates=(filing_source_date(filing.filing_date.isoformat()),),
            grade_rationale=(
                "Captured issuer-filed content; source reliability and underlying assertions "
                "have not been assessed. SEC hosting is not independent corroboration."
            ),
        )
        for index, event in enumerate(events)
    ]
    return InputExtraction(filing.primary_document, media_type, digest, tuple(events), limitations)
