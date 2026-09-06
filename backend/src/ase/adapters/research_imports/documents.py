"""Text-only PDF/DOCX extraction. Run only inside the isolated import worker."""

from __future__ import annotations

import io
import logging
import stat
import struct
import zipfile
from pathlib import PurePosixPath

# Element is a type only; actual XML parsing uses defusedxml below.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element  # nosec B405

import pypdf
import pypdf.filters
from defusedxml.ElementTree import fromstring

from ase.adapters.research_imports.models import (
    MAX_DEPTH,
    MAX_NODES,
    MAX_PAGES,
    MAX_XML_BYTES,
    MAX_ZIP_BYTES,
    MAX_ZIP_ENTRIES,
    ImportRejected,
    TextBudget,
)

WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _check_zip_directory(data: bytes) -> None:
    """Inspect bounded EOCD metadata before ZipFile allocates its entry inventory."""
    position = data.rfind(b"PK\x05\x06", max(0, len(data) - 65_557))
    if position < 0 or len(data) - position < 22:
        raise ImportRejected("DOCX has no valid archive directory.")
    disk, directory_disk, local_count, total_count, size, offset, comment = struct.unpack_from(
        "<4H2IH", data, position + 4
    )
    if (
        disk != 0
        or directory_disk != 0
        or local_count != total_count
        or total_count > MAX_ZIP_ENTRIES
        or size > MAX_XML_BYTES
        or offset + size > position
        or position + 22 + comment != len(data)
    ):
        raise ImportRejected("DOCX has an oversized or unsupported archive directory.")


def extract_pdf(data: bytes, budget: TextBudget) -> tuple[str, ...]:
    if not data.startswith(b"%PDF-"):
        raise ImportRejected("The upload is not a PDF document.")
    # pypdf's own bounded Flate decoder rejects expansion before allocating the full stream.
    # These process-local settings are changed only in the disposable worker and restored.
    original_limit = pypdf.filters.ZLIB_MAX_OUTPUT_LENGTH
    original_recovery = pypdf.filters.ZLIB_MAX_RECOVERY_INPUT_LENGTH
    logger = logging.getLogger("pypdf")
    previous_level = logger.level
    logger.setLevel(logging.CRITICAL)
    pypdf.filters.ZLIB_MAX_OUTPUT_LENGTH = MAX_XML_BYTES
    pypdf.filters.ZLIB_MAX_RECOVERY_INPUT_LENGTH = 100_000
    try:
        reader = pypdf.PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ImportRejected("Encrypted PDFs are unsupported.")
        if len(reader.pages) > MAX_PAGES:
            raise ImportRejected("PDF exceeds the page limit.")
        empty_pages = 0
        for number, page in enumerate(reader.pages, 1):
            contents = page.get_contents()
            if contents is not None and len(contents.get_data()) > MAX_XML_BYTES:
                raise ImportRejected("PDF page content exceeds the decoded size limit.")
            text = page.extract_text()
            if not text.strip():
                empty_pages += 1
            budget.add(f"PDF page {number}", text)
    finally:
        pypdf.filters.ZLIB_MAX_OUTPUT_LENGTH = original_limit
        pypdf.filters.ZLIB_MAX_RECOVERY_INPUT_LENGTH = original_recovery
        logger.setLevel(previous_level)
    limits = [
        "PDF references use physical page numbers, not printed page labels.",
        "Text extraction does not verify visual layout, reading order, signatures or authenticity.",
        "Images, scanned text, annotations, embedded files and form fields are not extracted.",
    ]
    if empty_pages:
        limits.append(f"{empty_pages} page(s) had no extractable text; OCR is not performed.")
    return tuple(limits)


def _document_xml(data: bytes) -> bytes:
    if not data.startswith(b"PK\x03\x04"):
        raise ImportRejected("The upload is not a DOCX document.")
    _check_zip_directory(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise ImportRejected("DOCX exceeds the archive entry limit.")
        total = 0
        names: set[str] = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (
                entry.filename in names
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in entry.orig_filename
                or "\x00" in entry.orig_filename
                or ":" in entry.filename
                or stat.S_ISLNK(mode)
                or entry.flag_bits & 1
            ):
                raise ImportRejected("DOCX contains an unsafe archive entry.")
            names.add(entry.filename)
            total += entry.file_size
            if (
                total > MAX_ZIP_BYTES
                or entry.file_size > MAX_XML_BYTES
                or entry.file_size > max(1, entry.compress_size) * 100
            ):
                raise ImportRejected("DOCX exceeds the archive expansion limit.")
            if entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ImportRejected("DOCX uses an unsupported compression method.")
        if "word/document.xml" not in names or "[Content_Types].xml" not in names:
            raise ImportRejected("DOCX is missing required document parts.")
        if any(name.lower().endswith("vbaproject.bin") for name in names):
            raise ImportRejected("Macro-enabled documents are unsupported.")
        with archive.open("word/document.xml") as stream:
            xml = stream.read(MAX_XML_BYTES + 1)
        if len(xml) > MAX_XML_BYTES:
            raise ImportRejected("DOCX document XML exceeds the size limit.")
        return xml


def _check_tree(root: Element) -> None:
    pending = [(root, 0)]
    visited = 0
    while pending:
        node, depth = pending.pop()
        visited += 1
        if depth > MAX_DEPTH or visited + len(pending) > MAX_NODES:
            raise ImportRejected("DOCX XML exceeds the structure limit.")
        pending.extend((child, depth + 1) for child in node)


def _paragraph(node: Element) -> str:
    parts: list[str] = []
    for child in node.iter():
        if child.tag == WORD + "t":
            parts.append(child.text or "")
        elif child.tag == WORD + "tab":
            parts.append("\t")
        elif child.tag in (WORD + "br", WORD + "cr"):
            parts.append("\n")
    return "".join(parts)


def extract_docx(data: bytes, budget: TextBudget) -> tuple[str, ...]:
    root = fromstring(_document_xml(data), forbid_dtd=True)
    _check_tree(root)
    body = root.find(WORD + "body")
    if root.tag != WORD + "document" or body is None:
        raise ImportRejected("DOCX has no supported Word document body.")
    # Document-order paragraph numbers include paragraphs in tables. They identify
    # structural source positions even when Word repaginates on a different device.
    for number, paragraph in enumerate(body.iter(WORD + "p"), 1):
        budget.add(f"DOCX body paragraph {number}", _paragraph(paragraph))
    return (
        "DOCX locators count body paragraphs in document order, including table cells.",
        "DOCX page numbers are unavailable because pagination depends on the layout renderer.",
        "Headers, footers, notes, comments, images, revision history and links are omitted.",
        "Table cells are extracted as paragraphs; table structure and layout are not verified.",
    )
