"""Bounded native UN consolidated and EU FSF 1.1 XML, without external entities.

Only identity names and list metadata are retained. Addresses, birth dates and
other unnecessary personal fields are not imported. Source URLs are never fetched.
"""

from datetime import datetime

# Types/exceptions only; parsing uses defusedxml with DTDs and entities forbidden.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring

from ase.adapters.research_records.designation_snapshot import (
    MAX_BYTES,
    MAX_ROWS,
    Authority,
    DesignationRecord,
    _cell,
)

EU_NAMESPACE = "http://eu.europa.ec/fpi/fsd/export"


def _value(node: Element, field: str) -> str:
    return _cell(node.findtext(field, default=""))


def _append(rows: list[DesignationRecord], record: DesignationRecord) -> None:
    if len(rows) >= MAX_ROWS:
        raise ValueError("Designation XML exceeds 100,000 named records")
    rows.append(record)


def _un(root: Element) -> tuple[DesignationRecord, ...]:
    if root.tag != "CONSOLIDATED_LIST":
        raise ValueError("Expected native UN consolidated XML")
    rows: list[DesignationRecord] = []
    for group, tag in (("INDIVIDUALS", "INDIVIDUAL"), ("ENTITIES", "ENTITY")):
        for node in root.findall(f"{group}/{tag}"):
            name = _cell(
                " ".join(
                    filter(
                        None,
                        (
                            _value(node, field)
                            for field in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")
                        ),
                    )
                )
            )
            identity = _value(node, "DATAID")
            programme = _value(node, "UN_LIST_TYPE")
            listed = _value(node, "LISTED_ON")
            updated = _value(node, "LAST_DAY_UPDATED/VALUE")
            native = _value(node, "NAME_ORIGINAL_SCRIPT")
            _append(
                rows,
                DesignationRecord(
                    identity,
                    name,
                    native,
                    tag.lower(),
                    programme,
                    listed,
                    updated,
                    "primary",
                ),
            )
            for alias in node.findall(f"{tag}_ALIAS/ALIAS_NAME"):
                if alias.text and alias.text.strip():
                    _append(
                        rows,
                        DesignationRecord(
                            identity,
                            _cell(alias.text),
                            "",
                            tag.lower(),
                            programme,
                            listed,
                            updated,
                            "alias",
                        ),
                    )
    return tuple(rows)


def _eu(root: Element) -> tuple[DesignationRecord, ...]:
    ns = f"{{{EU_NAMESPACE}}}"
    if root.tag != f"{ns}export":
        raise ValueError("Expected EU FSF 1.1 XML namespace")
    rows: list[DesignationRecord] = []
    for node in root.findall(f"{ns}sanctionEntity"):
        identity = _cell(node.get("logicalId", ""))
        subject = node.find(f"{ns}subjectType")
        kind = _cell(subject.get("code", "")) if subject is not None else ""
        regulation = node.find(f"{ns}regulation")
        programme = _cell(regulation.get("programme", "")) if regulation is not None else ""
        listed = _cell(regulation.get("publicationDate", "")) if regulation is not None else ""
        updated = _cell(node.get("lastUpdated", ""))
        for alias in node.findall(f"{ns}nameAlias"):
            name = _cell(alias.get("wholeName", ""))
            _append(
                rows,
                DesignationRecord(
                    identity,
                    name,
                    "",
                    kind,
                    programme,
                    listed,
                    updated,
                    "strong_alias" if alias.get("strong", "false") == "true" else "alias",
                ),
            )
    return tuple(rows)


def parse_xml(
    data: bytes, authority: Authority, published_at: datetime
) -> tuple[DesignationRecord, ...]:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Designation XML exceeds 32 MiB")
    try:
        root = fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (ParseError, DefusedXmlException) as exc:
        raise ValueError("Invalid or unsafe designation XML") from exc
    # Native export dates are verified where supplied; the operator must declare
    # an offset-aware publication date even when a source omits its timestamp.
    source_date = root.get("dateGenerated" if authority == "un_sc" else "generationDate")
    if source_date:
        try:
            declared = datetime.fromisoformat(source_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Invalid designation XML publication date") from exc
        if declared.date() != published_at.date():
            raise ValueError("XML publication date does not match declared publication date")
    if authority == "un_sc":
        return _un(root)
    if authority == "eu_fsf":
        return _eu(root)
    raise ValueError("Unsupported designation XML authority")
